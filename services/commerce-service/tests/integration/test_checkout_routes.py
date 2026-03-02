import pytest


@pytest.mark.asyncio
class TestCheckoutRoutes:
    async def _add_cart_item(self, client, headers):
        await client.post(
            "/cart/user1/items",
            headers=headers,
            json={
                "item_id": "pack-001",
                "item_type": "pack",
                "name": "Starter Pack",
                "quantity": 1,
                "unit_price": 4.99,
            },
        )

    async def test_validate_empty_cart(self, test_client, api_key_headers):
        resp = await test_client.post(
            "/checkout/user1/validate",
            headers=api_key_headers,
        )
        assert resp.status_code == 400
        assert "empty" in resp.json()["message"].lower()

    async def test_validate_cart_with_items(self, test_client, api_key_headers):
        await self._add_cart_item(test_client, api_key_headers)
        resp = await test_client.post(
            "/checkout/user1/validate",
            headers=api_key_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["valid"] is True

    async def test_create_payment(self, test_client, api_key_headers):
        await self._add_cart_item(test_client, api_key_headers)
        resp = await test_client.post(
            "/checkout/user1/create-payment",
            headers=api_key_headers,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "client_secret" in data
        assert "ephemeral_key" in data
        assert data["customer_id"] == "cus_test123"

    async def test_create_payment_empty_cart(self, test_client, api_key_headers):
        resp = await test_client.post(
            "/checkout/user1/create-payment",
            headers=api_key_headers,
        )
        assert resp.status_code == 400

    async def test_confirm_payment(self, test_client, api_key_headers):
        await self._add_cart_item(test_client, api_key_headers)
        await test_client.post(
            "/checkout/user1/create-payment",
            headers=api_key_headers,
        )
        resp = await test_client.post(
            "/checkout/user1/confirm",
            headers=api_key_headers,
            json={"payment_intent_id": "pi_test123"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "confirmed"
        assert data["order_id"].startswith("ORD-")

    async def test_confirm_missing_pi_id(self, test_client, api_key_headers):
        resp = await test_client.post(
            "/checkout/user1/confirm",
            headers=api_key_headers,
            json={},
        )
        assert resp.status_code == 400
        assert "payment_intent_id" in resp.json()["message"]

    async def test_full_checkout_flow(self, test_client, api_key_headers):
        # 1. Add item
        await self._add_cart_item(test_client, api_key_headers)

        # 2. Validate
        resp = await test_client.post(
            "/checkout/user1/validate", headers=api_key_headers
        )
        assert resp.json()["data"]["valid"] is True

        # 3. Create payment
        resp = await test_client.post(
            "/checkout/user1/create-payment", headers=api_key_headers
        )
        assert resp.status_code == 200

        # 4. Confirm
        resp = await test_client.post(
            "/checkout/user1/confirm",
            headers=api_key_headers,
            json={"payment_intent_id": "pi_test123"},
        )
        assert resp.status_code == 200

        # 5. Verify cart is cleared
        resp = await test_client.get("/cart/user1", headers=api_key_headers)
        assert resp.json()["data"]["items"] == []

        # 6. Verify order exists
        resp = await test_client.get("/orders/user1", headers=api_key_headers)
        assert len(resp.json()["data"]["orders"]) == 1
