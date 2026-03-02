import pytest


@pytest.mark.asyncio
class TestSubscriptionRoutes:
    async def test_get_no_subscription(self, test_client, api_key_headers):
        resp = await test_client.get(
            "/subscriptions/user1", headers=api_key_headers
        )
        assert resp.status_code == 404

    async def test_create_subscription(self, test_client, api_key_headers):
        resp = await test_client.post(
            "/subscriptions/user1/create",
            headers=api_key_headers,
            json={"tier": "premium"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["subscription_id"] == "sub_test123"
        assert "client_secret" in data

    async def test_create_subscription_invalid_tier(self, test_client, api_key_headers):
        resp = await test_client.post(
            "/subscriptions/user1/create",
            headers=api_key_headers,
            json={"tier": "invalid"},
        )
        assert resp.status_code == 400
        assert "Invalid tier" in resp.json()["message"]

    async def test_create_duplicate_subscription(self, test_client, api_key_headers, test_db):
        # Insert an active subscription
        await test_db.subscription_records.insert_one(
            {
                "user_id": "user1",
                "stripe_subscription_id": "sub_existing",
                "status": "active",
                "tier": "premium",
            }
        )
        resp = await test_client.post(
            "/subscriptions/user1/create",
            headers=api_key_headers,
            json={"tier": "ultra"},
        )
        assert resp.status_code == 400
        assert "active subscription" in resp.json()["message"].lower()

    async def test_cancel_subscription(self, test_client, api_key_headers, test_db):
        await test_db.subscription_records.insert_one(
            {
                "user_id": "user1",
                "stripe_subscription_id": "sub_cancel",
                "status": "active",
                "tier": "premium",
            }
        )
        resp = await test_client.post(
            "/subscriptions/user1/cancel", headers=api_key_headers
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["cancel_at_period_end"] is True

    async def test_cancel_no_subscription(self, test_client, api_key_headers):
        resp = await test_client.post(
            "/subscriptions/user1/cancel", headers=api_key_headers
        )
        assert resp.status_code == 400

    async def test_reactivate_subscription(self, test_client, api_key_headers, test_db):
        await test_db.subscription_records.insert_one(
            {
                "user_id": "user1",
                "stripe_subscription_id": "sub_react",
                "status": "active",
                "tier": "premium",
                "cancel_at_period_end": True,
            }
        )
        resp = await test_client.post(
            "/subscriptions/user1/reactivate", headers=api_key_headers
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["cancel_at_period_end"] is False

    async def test_change_tier(self, test_client, api_key_headers, test_db):
        await test_db.subscription_records.insert_one(
            {
                "user_id": "user1",
                "stripe_subscription_id": "sub_change",
                "stripe_customer_id": "cus_123",
                "status": "active",
                "tier": "premium",
            }
        )
        resp = await test_client.post(
            "/subscriptions/user1/change-tier",
            headers=api_key_headers,
            json={"new_tier": "ultra"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["tier"] == "ultra"

    async def test_change_to_same_tier(self, test_client, api_key_headers, test_db):
        await test_db.subscription_records.insert_one(
            {
                "user_id": "user1",
                "stripe_subscription_id": "sub_same",
                "status": "active",
                "tier": "premium",
            }
        )
        resp = await test_client.post(
            "/subscriptions/user1/change-tier",
            headers=api_key_headers,
            json={"new_tier": "premium"},
        )
        assert resp.status_code == 400

    async def test_requires_auth(self, test_client):
        resp = await test_client.get("/subscriptions/user1")
        assert resp.status_code == 401
