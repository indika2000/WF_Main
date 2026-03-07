"""Integration tests for the /generate endpoint."""

import pytest


class TestGenerateEndpoint:
    """Test the full barcode → creature generation flow."""

    async def test_generate_new_creature(self, test_client, auth_headers):
        resp = await test_client.post(
            "/generate",
            json={"code_type": "EAN_13", "raw_value": "5012345678900"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["is_new_discovery"] is True
        assert data["data"]["is_owner"] is True
        assert data["data"]["is_claimed_variant"] is False
        creature = data["data"]["creature"]
        assert creature["identity"]["creature_id"].startswith("WF-v1-")
        assert creature["classification"]["rarity"] in [
            "COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY"
        ]

    async def test_generate_idempotent_same_user(self, test_client, auth_headers):
        """Same user scanning same barcode twice gets the same creature."""
        resp1 = await test_client.post(
            "/generate",
            json={"code_type": "EAN_13", "raw_value": "5012345678900"},
            headers=auth_headers,
        )
        resp2 = await test_client.post(
            "/generate",
            json={"code_type": "EAN_13", "raw_value": "5012345678900"},
            headers=auth_headers,
        )
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        id1 = resp1.json()["data"]["creature"]["identity"]["creature_id"]
        id2 = resp2.json()["data"]["creature"]["identity"]["creature_id"]
        assert id1 == id2
        assert resp2.json()["data"]["is_new_discovery"] is False

    async def test_generate_claimed_variant_different_user(
        self, test_client, auth_headers, auth_headers_user2
    ):
        """Second user scanning same barcode gets a Common variant."""
        # User 1 scans first
        resp1 = await test_client.post(
            "/generate",
            json={"code_type": "EAN_13", "raw_value": "5012345678900"},
            headers=auth_headers,
        )
        assert resp1.status_code == 200

        # User 2 scans same barcode
        resp2 = await test_client.post(
            "/generate",
            json={"code_type": "EAN_13", "raw_value": "5012345678900"},
            headers=auth_headers_user2,
        )
        assert resp2.status_code == 200
        data2 = resp2.json()["data"]
        assert data2["is_claimed_variant"] is True
        assert data2["creature"]["classification"]["rarity"] == "COMMON"

        # Different creature IDs
        id1 = resp1.json()["data"]["creature"]["identity"]["creature_id"]
        id2 = data2["creature"]["identity"]["creature_id"]
        assert id1 != id2

    async def test_generate_invalid_barcode(self, test_client, auth_headers):
        resp = await test_client.post(
            "/generate",
            json={"code_type": "EAN_13", "raw_value": "invalid"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "INVALID_BARCODE"

    async def test_generate_unsupported_code_type(self, test_client, auth_headers):
        resp = await test_client.post(
            "/generate",
            json={"code_type": "CODE_128", "raw_value": "12345"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    async def test_generate_upc_a(self, test_client, auth_headers):
        resp = await test_client.post(
            "/generate",
            json={"code_type": "UPC_A", "raw_value": "012345678905"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["is_new_discovery"] is True

    async def test_generate_qr(self, test_client, auth_headers):
        resp = await test_client.post(
            "/generate",
            json={"code_type": "QR", "raw_value": "https://example.com/product/42"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["is_new_discovery"] is True

    async def test_generate_requires_auth(self, test_client):
        resp = await test_client.post(
            "/generate",
            json={"code_type": "EAN_13", "raw_value": "5012345678900"},
        )
        assert resp.status_code == 401

    async def test_different_barcodes_different_creatures(
        self, test_client, auth_headers
    ):
        """Different barcodes produce different creatures."""
        resp1 = await test_client.post(
            "/generate",
            json={"code_type": "EAN_13", "raw_value": "5012345678900"},
            headers=auth_headers,
        )
        resp2 = await test_client.post(
            "/generate",
            json={"code_type": "EAN_13", "raw_value": "4006381333931"},
            headers=auth_headers,
        )
        id1 = resp1.json()["data"]["creature"]["identity"]["creature_id"]
        id2 = resp2.json()["data"]["creature"]["identity"]["creature_id"]
        assert id1 != id2


class TestCollectionEndpoint:
    """Test the /collection endpoint."""

    async def test_empty_collection(self, test_client, auth_headers):
        resp = await test_client.get("/collection", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 0
        assert data["items"] == []

    async def test_collection_after_generate(self, test_client, auth_headers):
        # Generate a creature
        await test_client.post(
            "/generate",
            json={"code_type": "EAN_13", "raw_value": "5012345678900"},
            headers=auth_headers,
        )

        resp = await test_client.get("/collection", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 1

    async def test_collection_pagination(self, test_client, auth_headers):
        # Generate 3 creatures
        for barcode in ["5012345678900", "4006381333931", "0000000000000"]:
            await test_client.post(
                "/generate",
                json={"code_type": "EAN_13", "raw_value": barcode},
                headers=auth_headers,
            )

        resp = await test_client.get(
            "/collection?skip=0&limit=2", headers=auth_headers
        )
        data = resp.json()["data"]
        assert data["total"] == 3
        assert len(data["items"]) == 2


class TestCreaturesEndpoint:
    """Test the /creatures/:id endpoint."""

    async def test_get_creature_by_id(self, test_client, auth_headers):
        # Generate first
        gen_resp = await test_client.post(
            "/generate",
            json={"code_type": "EAN_13", "raw_value": "5012345678900"},
            headers=auth_headers,
        )
        creature_id = gen_resp.json()["data"]["creature"]["identity"]["creature_id"]

        # Fetch by ID
        resp = await test_client.get(
            f"/creatures/{creature_id}", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["creature"]["identity"]["creature_id"] == creature_id
        assert resp.json()["data"]["is_owner"] is True

    async def test_get_nonexistent_creature(self, test_client, auth_headers):
        resp = await test_client.get(
            "/creatures/WF-v1-COMMON-FOREST-WOLF-DEADBEEF",
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestSupplyEndpoint:
    """Test the /supply endpoint."""

    async def test_supply_status(self, test_client, auth_headers):
        resp = await test_client.get("/supply", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["season"] == "v1"
        assert len(data["tiers"]) == 5
        # All should start at 0
        for tier in data["tiers"]:
            assert tier["current_count"] == 0


class TestHealthEndpoint:
    """Test health endpoints."""

    async def test_health_check(self, test_client):
        resp = await test_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "ok"

    async def test_health_detailed(self, test_client):
        resp = await test_client.get("/health/detailed")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "generation_config" in data["checks"]
