import pytest


class TestSubscriptionRoutes:
    @pytest.mark.asyncio
    async def test_create_subscription(self, test_client, api_key_headers):
        # Create user first
        await test_client.post(
            "/permissions/user123",
            headers=api_key_headers,
            json={"email": "test@example.com"},
        )
        # Update subscription to premium
        response = await test_client.post(
            "/subscriptions/user123",
            headers=api_key_headers,
            json={"tier": "premium"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["tier"] == "premium"

    @pytest.mark.asyncio
    async def test_get_subscription(self, test_client, api_key_headers):
        # Create user (which creates free subscription)
        await test_client.post(
            "/permissions/user123",
            headers=api_key_headers,
            json={},
        )
        response = await test_client.get(
            "/subscriptions/user123", headers=api_key_headers
        )
        assert response.status_code == 200
        assert response.json()["data"]["tier"] == "free"

    @pytest.mark.asyncio
    async def test_subscription_syncs_permissions(self, test_client, api_key_headers):
        # Create user
        await test_client.post(
            "/permissions/user123",
            headers=api_key_headers,
            json={},
        )
        # Upgrade to premium
        await test_client.post(
            "/subscriptions/user123",
            headers=api_key_headers,
            json={"tier": "premium"},
        )
        # Check permissions were synced
        response = await test_client.get(
            "/permissions/user123", headers=api_key_headers
        )
        perms = response.json()["data"]["permissions"]
        assert perms["ad_free"] is True
        assert perms["ai_image_generation"] is True

    @pytest.mark.asyncio
    async def test_invalid_tier_returns_400(self, test_client, api_key_headers):
        response = await test_client.post(
            "/subscriptions/user123",
            headers=api_key_headers,
            json={"tier": "nonexistent"},
        )
        assert response.status_code == 400
        assert response.json()["error_code"] == "INVALID_TIER"

    @pytest.mark.asyncio
    async def test_list_tiers(self, test_client, api_key_headers):
        response = await test_client.get(
            "/subscriptions/tiers", headers=api_key_headers
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "free" in data
        assert "premium" in data
        assert "ultra" in data

    @pytest.mark.asyncio
    async def test_force_sync(self, test_client, api_key_headers):
        # Create user
        await test_client.post(
            "/permissions/user123",
            headers=api_key_headers,
            json={},
        )
        response = await test_client.post(
            "/subscriptions/user123/sync", headers=api_key_headers
        )
        assert response.status_code == 200
