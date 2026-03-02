import pytest

from app.models.cart import CartItemAdd
from app.services import cart_service


@pytest.mark.asyncio
class TestCartService:
    async def test_get_cart_empty(self, test_redis):
        cart = await cart_service.get_cart("user1", test_redis)
        assert cart is None

    async def test_add_item(self, test_redis):
        item = CartItemAdd(
            item_id="pack-001",
            item_type="pack",
            name="Starter Pack",
            quantity=1,
            unit_price=4.99,
        )
        cart = await cart_service.add_item("user1", item, test_redis)
        assert len(cart.items) == 1
        assert cart.items[0].item_id == "pack-001"
        assert cart.subtotal == 4.99
        assert cart.total == 4.99

    async def test_add_item_merge_quantity(self, test_redis):
        item = CartItemAdd(
            item_id="pack-001",
            item_type="pack",
            name="Starter Pack",
            quantity=1,
            unit_price=4.99,
        )
        await cart_service.add_item("user1", item, test_redis)
        cart = await cart_service.add_item("user1", item, test_redis)
        assert len(cart.items) == 1
        assert cart.items[0].quantity == 2
        assert cart.subtotal == pytest.approx(9.98)

    async def test_add_multiple_items(self, test_redis):
        item1 = CartItemAdd(
            item_id="pack-001",
            item_type="pack",
            name="Starter Pack",
            quantity=1,
            unit_price=4.99,
        )
        item2 = CartItemAdd(
            item_id="card-001",
            item_type="one_time",
            name="Rare Card",
            quantity=2,
            unit_price=1.99,
        )
        await cart_service.add_item("user1", item1, test_redis)
        cart = await cart_service.add_item("user1", item2, test_redis)
        assert len(cart.items) == 2
        assert cart.subtotal == pytest.approx(4.99 + 1.99 * 2)

    async def test_update_item_quantity(self, test_redis):
        item = CartItemAdd(
            item_id="pack-001",
            item_type="pack",
            name="Starter Pack",
            quantity=1,
            unit_price=4.99,
        )
        await cart_service.add_item("user1", item, test_redis)
        cart = await cart_service.update_item("user1", "pack-001", 5, test_redis)
        assert cart.items[0].quantity == 5
        assert cart.subtotal == pytest.approx(4.99 * 5)

    async def test_update_item_zero_removes(self, test_redis):
        item = CartItemAdd(
            item_id="pack-001",
            item_type="pack",
            name="Starter Pack",
            quantity=1,
            unit_price=4.99,
        )
        await cart_service.add_item("user1", item, test_redis)
        cart = await cart_service.update_item("user1", "pack-001", 0, test_redis)
        assert len(cart.items) == 0
        assert cart.total == 0.0

    async def test_update_nonexistent_cart(self, test_redis):
        result = await cart_service.update_item("nobody", "pack-001", 1, test_redis)
        assert result is None

    async def test_remove_item(self, test_redis):
        item = CartItemAdd(
            item_id="pack-001",
            item_type="pack",
            name="Starter Pack",
            quantity=1,
            unit_price=4.99,
        )
        await cart_service.add_item("user1", item, test_redis)
        cart = await cart_service.remove_item("user1", "pack-001", test_redis)
        assert len(cart.items) == 0

    async def test_remove_nonexistent_item(self, test_redis):
        item = CartItemAdd(
            item_id="pack-001",
            item_type="pack",
            name="Starter Pack",
            quantity=1,
            unit_price=4.99,
        )
        await cart_service.add_item("user1", item, test_redis)
        result = await cart_service.remove_item("user1", "nonexistent", test_redis)
        assert result is None

    async def test_clear_cart(self, test_redis):
        item = CartItemAdd(
            item_id="pack-001",
            item_type="pack",
            name="Starter Pack",
            quantity=1,
            unit_price=4.99,
        )
        await cart_service.add_item("user1", item, test_redis)
        cleared = await cart_service.clear_cart("user1", test_redis)
        assert cleared is True
        cart = await cart_service.get_cart("user1", test_redis)
        assert cart is None

    async def test_clear_empty_cart(self, test_redis):
        cleared = await cart_service.clear_cart("nobody", test_redis)
        assert cleared is False

    async def test_cart_persists_in_redis(self, test_redis):
        item = CartItemAdd(
            item_id="pack-001",
            item_type="pack",
            name="Starter Pack",
            quantity=1,
            unit_price=4.99,
        )
        await cart_service.add_item("user1", item, test_redis)
        # Verify it exists in Redis
        data = await test_redis.get("cart:user1")
        assert data is not None
        # Retrieve via service
        cart = await cart_service.get_cart("user1", test_redis)
        assert cart.items[0].name == "Starter Pack"
