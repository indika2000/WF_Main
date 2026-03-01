import pytest


class TestUsageRoutes:
    @pytest.mark.asyncio
    async def test_get_usage(self, test_client, api_key_headers):
        # Create user (initializes usage records)
        await test_client.post(
            "/permissions/user123",
            headers=api_key_headers,
            json={},
        )
        response = await test_client.get(
            "/usage/user123/ai_text_generation", headers=api_key_headers
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["used"] == 0
        assert data["limit"] == 10  # Free tier

    @pytest.mark.asyncio
    async def test_record_usage(self, test_client, api_key_headers):
        await test_client.post(
            "/permissions/user123",
            headers=api_key_headers,
            json={},
        )
        response = await test_client.post(
            "/usage/user123/ai_text_generation/record",
            headers=api_key_headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["used"] == 1

    @pytest.mark.asyncio
    async def test_check_usage_allowed(self, test_client, api_key_headers):
        await test_client.post(
            "/permissions/user123",
            headers=api_key_headers,
            json={},
        )
        response = await test_client.post(
            "/usage/user123/ai_text_generation/check",
            headers=api_key_headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["allowed"] is True
        assert data["remaining"] == 10

    @pytest.mark.asyncio
    async def test_check_usage_at_limit(self, test_client, api_key_headers):
        await test_client.post(
            "/permissions/user123",
            headers=api_key_headers,
            json={},
        )
        # Exhaust all free uses
        for _ in range(10):
            await test_client.post(
                "/usage/user123/ai_text_generation/record",
                headers=api_key_headers,
            )
        response = await test_client.post(
            "/usage/user123/ai_text_generation/check",
            headers=api_key_headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["allowed"] is False
        assert data["remaining"] == 0
        assert data["reason"] == "limit_reached"

    @pytest.mark.asyncio
    async def test_add_bonus(self, test_client, api_key_headers):
        await test_client.post(
            "/permissions/user123",
            headers=api_key_headers,
            json={},
        )
        response = await test_client.post(
            "/usage/user123/ai_text_generation/bonus",
            headers=api_key_headers,
            json={"amount": 5},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["bonus"] == 5

    @pytest.mark.asyncio
    async def test_usage_not_found(self, test_client, api_key_headers):
        response = await test_client.get(
            "/usage/user123/nonexistent_feature",
            headers=api_key_headers,
        )
        assert response.status_code == 404
