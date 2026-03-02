import pytest


@pytest.mark.asyncio
class TestOrderRoutes:
    async def test_list_no_orders(self, test_client, api_key_headers):
        resp = await test_client.get("/orders/user1", headers=api_key_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["orders"] == []
        assert data["total"] == 0

    async def test_list_orders(self, test_client, api_key_headers, test_db):
        await test_db.orders.insert_many(
            [
                {"order_id": "ORD-001", "user_id": "user1", "status": "confirmed", "created_at": "2026-01-01T00:00:00"},
                {"order_id": "ORD-002", "user_id": "user1", "status": "completed", "created_at": "2026-01-02T00:00:00"},
                {"order_id": "ORD-003", "user_id": "user2", "status": "confirmed", "created_at": "2026-01-01T00:00:00"},
            ]
        )
        resp = await test_client.get("/orders/user1", headers=api_key_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 2
        assert len(data["orders"]) == 2

    async def test_list_orders_pagination(self, test_client, api_key_headers, test_db):
        orders = [
            {"order_id": f"ORD-{i:03d}", "user_id": "user1", "status": "confirmed", "created_at": f"2026-01-{i+1:02d}T00:00:00"}
            for i in range(5)
        ]
        await test_db.orders.insert_many(orders)
        resp = await test_client.get(
            "/orders/user1?page=1&limit=2", headers=api_key_headers
        )
        data = resp.json()["data"]
        assert len(data["orders"]) == 2
        assert data["total"] == 5

    async def test_get_order(self, test_client, api_key_headers, test_db):
        await test_db.orders.insert_one(
            {"order_id": "ORD-GET-001", "user_id": "user1", "status": "confirmed"}
        )
        resp = await test_client.get(
            "/orders/user1/ORD-GET-001", headers=api_key_headers
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["order_id"] == "ORD-GET-001"

    async def test_get_order_not_found(self, test_client, api_key_headers):
        resp = await test_client.get(
            "/orders/user1/ORD-NONEXIST", headers=api_key_headers
        )
        assert resp.status_code == 404

    async def test_get_order_wrong_user(self, test_client, api_key_headers, test_db):
        await test_db.orders.insert_one(
            {"order_id": "ORD-OTHER", "user_id": "user2", "status": "confirmed"}
        )
        resp = await test_client.get(
            "/orders/user1/ORD-OTHER", headers=api_key_headers
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestProfileRoutes:
    async def test_get_empty_profile(self, test_client, api_key_headers):
        resp = await test_client.get("/profile/user1", headers=api_key_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["user_id"] == "user1"
        assert data["addresses"] == []

    async def test_add_address(self, test_client, api_key_headers):
        resp = await test_client.post(
            "/profile/user1/addresses",
            headers=api_key_headers,
            json={
                "label": "Home",
                "line1": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "postal_code": "12345",
            },
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["label"] == "Home"
        assert "id" in data

    async def test_delete_address(self, test_client, api_key_headers, test_db):
        await test_db.commerce_profiles.insert_one(
            {
                "user_id": "user1",
                "addresses": [
                    {"id": "addr-1", "label": "Home", "line1": "123 Main", "city": "X", "state": "CA", "postal_code": "12345", "country": "US", "is_default": False}
                ],
            }
        )
        resp = await test_client.delete(
            "/profile/user1/addresses/addr-1", headers=api_key_headers
        )
        assert resp.status_code == 200

    async def test_delete_nonexistent_address(self, test_client, api_key_headers):
        resp = await test_client.delete(
            "/profile/user1/addresses/nonexistent", headers=api_key_headers
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestWebhookRoutes:
    async def test_webhook_no_signature(self, test_client):
        resp = await test_client.post(
            "/webhooks/stripe",
            content=b'{"type": "test"}',
            headers={"Content-Type": "application/json"},
        )
        # Should fail with invalid signature, NOT 401 (no auth required)
        assert resp.status_code == 400
        assert resp.json()["error_code"] in ("INVALID_SIGNATURE", "INVALID_PAYLOAD")

    async def test_webhook_requires_no_auth(self, test_client):
        # Webhook endpoint should be accessible without auth headers
        resp = await test_client.post(
            "/webhooks/stripe",
            content=b'{}',
            headers={"Content-Type": "application/json"},
        )
        # Should NOT be 401
        assert resp.status_code != 401
