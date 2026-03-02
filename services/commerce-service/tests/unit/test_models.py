import pytest

from app.models.cart import Cart, CartItem, CartItemAdd, CartItemUpdate
from app.models.orders import (
    Order,
    OrderItem,
    SubscriptionRecord,
    generate_order_id,
)
from app.models.profile import Address, AddressCreate, CommerceProfile


class TestCartModels:
    def test_cart_defaults(self):
        cart = Cart(user_id="user1")
        assert cart.user_id == "user1"
        assert cart.items == []
        assert cart.subtotal == 0.0
        assert cart.total == 0.0

    def test_cart_item(self):
        item = CartItem(
            item_id="pack-001",
            item_type="pack",
            name="Starter Pack",
            quantity=2,
            unit_price=4.99,
        )
        assert item.item_id == "pack-001"
        assert item.quantity == 2
        assert item.metadata == {}

    def test_cart_item_add(self):
        add = CartItemAdd(
            item_id="p1",
            item_type="one_time",
            name="Test",
            quantity=1,
            unit_price=9.99,
        )
        assert add.item_id == "p1"

    def test_cart_item_update(self):
        update = CartItemUpdate(quantity=5)
        assert update.quantity == 5


class TestOrderModels:
    def test_generate_order_id(self):
        oid = generate_order_id()
        assert oid.startswith("ORD-")
        parts = oid.split("-")
        assert len(parts) == 3
        assert len(parts[2]) == 6  # hex suffix

    def test_generate_order_id_uniqueness(self):
        ids = {generate_order_id() for _ in range(100)}
        assert len(ids) == 100

    def test_order_defaults(self):
        order = Order(user_id="user1")
        assert order.order_id.startswith("ORD-")
        assert order.status == "pending"
        assert order.order_type == "one_time"
        assert order.items == []

    def test_order_item(self):
        item = OrderItem(
            item_id="p1",
            item_type="pack",
            name="Starter",
            quantity=1,
            unit_price=4.99,
            total_price=4.99,
        )
        assert item.total_price == 4.99

    def test_subscription_record(self):
        record = SubscriptionRecord(
            user_id="user1",
            stripe_subscription_id="sub_123",
            stripe_customer_id="cus_123",
            tier="premium",
        )
        assert record.status == "active"
        assert record.cancel_at_period_end is False


class TestProfileModels:
    def test_commerce_profile(self):
        profile = CommerceProfile(user_id="user1")
        assert profile.stripe_customer_id is None
        assert profile.addresses == []

    def test_address(self):
        addr = Address(
            label="Home",
            line1="123 Main St",
            city="Anytown",
            state="CA",
            postal_code="12345",
        )
        assert addr.country == "US"
        assert addr.is_default is False
        assert addr.id  # UUID auto-generated

    def test_address_create(self):
        create = AddressCreate(
            label="Work",
            line1="456 Office Blvd",
            city="Workville",
            state="NY",
            postal_code="67890",
        )
        assert create.label == "Work"
