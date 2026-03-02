import logging
import uuid
from datetime import datetime, timezone

import stripe
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from app.models.orders import Order, OrderItem, generate_order_id
from app.services import cart_service

logger = logging.getLogger("commerce")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _get_or_create_customer(user_id: str, db: AsyncIOMotorDatabase) -> str:
    """Get existing Stripe customer or create a new one."""
    profile = await db.commerce_profiles.find_one({"user_id": user_id})
    if profile and profile.get("stripe_customer_id"):
        return profile["stripe_customer_id"]

    customer = stripe.Customer.create(metadata={"firebase_uid": user_id})

    await db.commerce_profiles.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "stripe_customer_id": customer.id,
                "updated_at": _utcnow(),
            },
            "$setOnInsert": {
                "created_at": _utcnow(),
                "addresses": [],
                "default_payment_method_id": None,
            },
        },
        upsert=True,
    )
    return customer.id


async def validate_cart(
    user_id: str, r: Redis, db: AsyncIOMotorDatabase
) -> dict:
    """Validate the cart is ready for checkout."""
    cart = await cart_service.get_cart(user_id, r)
    if cart is None or len(cart.items) == 0:
        return {"valid": False, "error": "Cart is empty"}

    if cart.total <= 0:
        return {"valid": False, "error": "Cart total must be greater than zero"}

    return {"valid": True, "cart": cart.model_dump(mode="json")}


async def create_payment(
    user_id: str, r: Redis, db: AsyncIOMotorDatabase
) -> dict:
    """Create a Stripe PaymentIntent for the cart contents."""
    cart = await cart_service.get_cart(user_id, r)
    if cart is None or len(cart.items) == 0:
        raise ValueError("Cart is empty")

    customer_id = await _get_or_create_customer(user_id, db)

    # Amount in cents
    amount_cents = int(round(cart.total * 100))

    idempotency_key = f"pi_{user_id}_{uuid.uuid4().hex[:12]}"

    payment_intent = stripe.PaymentIntent.create(
        amount=amount_cents,
        currency="usd",
        customer=customer_id,
        metadata={"user_id": user_id, "order_type": "one_time"},
        automatic_payment_methods={"enabled": True},
        idempotency_key=idempotency_key,
    )

    ephemeral_key = stripe.EphemeralKey.create(
        customer=customer_id,
        stripe_version="2024-06-20",
    )

    return {
        "client_secret": payment_intent.client_secret,
        "ephemeral_key": ephemeral_key.secret,
        "customer_id": customer_id,
        "payment_intent_id": payment_intent.id,
        "amount": amount_cents,
    }


async def confirm_payment(
    user_id: str,
    payment_intent_id: str,
    r: Redis,
    db: AsyncIOMotorDatabase,
) -> dict:
    """Confirm payment succeeded and create an order record."""
    # Verify payment intent status
    pi = stripe.PaymentIntent.retrieve(payment_intent_id)
    if pi.status != "succeeded":
        raise ValueError(f"Payment not succeeded, status: {pi.status}")

    # Get cart for order snapshot
    cart = await cart_service.get_cart(user_id, r)
    if cart is None:
        raise ValueError("Cart not found")

    # Build order items from cart
    order_items = [
        OrderItem(
            item_id=item.item_id,
            item_type=item.item_type,
            name=item.name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.unit_price * item.quantity,
            metadata=item.metadata,
        )
        for item in cart.items
    ]

    # Get payment method summary
    payment_method_summary = None
    if pi.payment_method:
        try:
            pm = stripe.PaymentMethod.retrieve(pi.payment_method)
            if pm.card:
                payment_method_summary = (
                    f"{pm.card.brand.title()} ****{pm.card.last4}"
                )
        except Exception:
            pass

    # Create order
    order = Order(
        user_id=user_id,
        stripe_payment_intent_id=payment_intent_id,
        order_type="one_time",
        status="confirmed",
        items=order_items,
        subtotal=cart.subtotal,
        tax=cart.tax,
        shipping=cart.shipping,
        total=cart.total,
        payment_method_summary=payment_method_summary,
    )

    await db.orders.insert_one(order.model_dump(mode="json"))

    # Clear cart after successful order
    await cart_service.clear_cart(user_id, r)

    logger.info("Order %s created for user %s", order.order_id, user_id)
    return order.model_dump(mode="json")
