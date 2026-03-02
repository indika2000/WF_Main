import pytest


@pytest.mark.asyncio
class TestCartRoutes:
    async def test_get_empty_cart(self, test_client, api_key_headers):
        resp = await test_client.get("/cart/user1", headers=api_key_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["items"] == []

    async def test_add_item(self, test_client, api_key_headers):
        resp = await test_client.post(
            "/cart/user1/items",
            headers=api_key_headers,
            json={
                "item_id": "pack-001",
                "item_type": "pack",
                "name": "Starter Pack",
                "quantity": 1,
                "unit_price": 4.99,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["data"]["items"]) == 1
        assert data["data"]["total"] == pytest.approx(4.99)

    async def test_add_multiple_items(self, test_client, api_key_headers):
        await test_client.post(
            "/cart/user1/items",
            headers=api_key_headers,
            json={
                "item_id": "pack-001",
                "item_type": "pack",
                "name": "Starter Pack",
                "quantity": 1,
                "unit_price": 4.99,
            },
        )
        resp = await test_client.post(
            "/cart/user1/items",
            headers=api_key_headers,
            json={
                "item_id": "card-001",
                "item_type": "one_time",
                "name": "Rare Card",
                "quantity": 1,
                "unit_price": 1.99,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]["items"]) == 2

    async def test_update_item_quantity(self, test_client, api_key_headers):
        await test_client.post(
            "/cart/user1/items",
            headers=api_key_headers,
            json={
                "item_id": "pack-001",
                "item_type": "pack",
                "name": "Starter Pack",
                "quantity": 1,
                "unit_price": 4.99,
            },
        )
        resp = await test_client.patch(
            "/cart/user1/items/pack-001",
            headers=api_key_headers,
            json={"quantity": 3},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["items"][0]["quantity"] == 3
        assert data["data"]["total"] == pytest.approx(4.99 * 3)

    async def test_remove_item(self, test_client, api_key_headers):
        await test_client.post(
            "/cart/user1/items",
            headers=api_key_headers,
            json={
                "item_id": "pack-001",
                "item_type": "pack",
                "name": "Starter Pack",
                "quantity": 1,
                "unit_price": 4.99,
            },
        )
        resp = await test_client.delete(
            "/cart/user1/items/pack-001",
            headers=api_key_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]["items"]) == 0

    async def test_remove_nonexistent_item(self, test_client, api_key_headers):
        resp = await test_client.delete(
            "/cart/user1/items/nonexistent",
            headers=api_key_headers,
        )
        assert resp.status_code == 404

    async def test_clear_cart(self, test_client, api_key_headers):
        await test_client.post(
            "/cart/user1/items",
            headers=api_key_headers,
            json={
                "item_id": "pack-001",
                "item_type": "pack",
                "name": "Starter Pack",
                "quantity": 1,
                "unit_price": 4.99,
            },
        )
        resp = await test_client.delete("/cart/user1", headers=api_key_headers)
        assert resp.status_code == 200

        # Verify empty
        resp = await test_client.get("/cart/user1", headers=api_key_headers)
        assert resp.json()["data"]["items"] == []

    async def test_requires_auth(self, test_client):
        resp = await test_client.get("/cart/user1")
        assert resp.status_code == 401
