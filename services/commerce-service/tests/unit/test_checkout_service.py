import pytest

from app.models.cart import CartItemAdd
from app.services import cart_service, checkout_service


@pytest.mark.asyncio
class TestCheckoutService:
    async def test_validate_empty_cart(self, test_redis, test_db):
        result = await checkout_service.validate_cart("user1", test_redis, test_db)
        assert result["valid"] is False
        assert "empty" in result["error"].lower()

    async def test_validate_cart_with_items(self, test_redis, test_db):
        item = CartItemAdd(
            item_id="pack-001",
            item_type="pack",
            name="Starter Pack",
            quantity=1,
            unit_price=4.99,
        )
        await cart_service.add_item("user1", item, test_redis)
        result = await checkout_service.validate_cart("user1", test_redis, test_db)
        assert result["valid"] is True

    async def test_create_payment(self, test_redis, test_db):
        item = CartItemAdd(
            item_id="pack-001",
            item_type="pack",
            name="Starter Pack",
            quantity=1,
            unit_price=4.99,
        )
        await cart_service.add_item("user1", item, test_redis)
        result = await checkout_service.create_payment("user1", test_redis, test_db)
        assert "client_secret" in result
        assert "ephemeral_key" in result
        assert "customer_id" in result
        assert result["customer_id"] == "cus_test123"

    async def test_create_payment_empty_cart_raises(self, test_redis, test_db):
        with pytest.raises(ValueError, match="Cart is empty"):
            await checkout_service.create_payment("user1", test_redis, test_db)

    async def test_create_payment_creates_profile(self, test_redis, test_db):
        item = CartItemAdd(
            item_id="pack-001",
            item_type="pack",
            name="Starter Pack",
            quantity=1,
            unit_price=4.99,
        )
        await cart_service.add_item("user1", item, test_redis)
        await checkout_service.create_payment("user1", test_redis, test_db)

        profile = await test_db.commerce_profiles.find_one({"user_id": "user1"})
        assert profile is not None
        assert profile["stripe_customer_id"] == "cus_test123"

    async def test_confirm_payment(self, test_redis, test_db):
        item = CartItemAdd(
            item_id="pack-001",
            item_type="pack",
            name="Starter Pack",
            quantity=1,
            unit_price=4.99,
        )
        await cart_service.add_item("user1", item, test_redis)
        await checkout_service.create_payment("user1", test_redis, test_db)

        order = await checkout_service.confirm_payment(
            "user1", "pi_test123", test_redis, test_db
        )
        assert order["status"] == "confirmed"
        assert order["order_id"].startswith("ORD-")
        assert len(order["items"]) == 1
        assert order["total"] == pytest.approx(4.99)

        # Cart should be cleared
        cart = await cart_service.get_cart("user1", test_redis)
        assert cart is None

    async def test_confirm_payment_creates_order_in_db(self, test_redis, test_db):
        item = CartItemAdd(
            item_id="pack-001",
            item_type="pack",
            name="Starter Pack",
            quantity=1,
            unit_price=4.99,
        )
        await cart_service.add_item("user1", item, test_redis)
        await checkout_service.create_payment("user1", test_redis, test_db)
        order = await checkout_service.confirm_payment(
            "user1", "pi_test123", test_redis, test_db
        )

        db_order = await test_db.orders.find_one({"order_id": order["order_id"]})
        assert db_order is not None
        assert db_order["user_id"] == "user1"
