import logging
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.orders import Order, OrderItem, SubscriptionRecord, generate_order_id

logger = logging.getLogger("commerce")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ts_to_dt(ts: int | None) -> datetime | None:
    """Convert Unix timestamp to datetime."""
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


async def handle_event(event: dict, db: AsyncIOMotorDatabase) -> None:
    """Dispatch Stripe webhook event to appropriate handler."""
    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    handlers = {
        "payment_intent.succeeded": _handle_payment_succeeded,
        "payment_intent.payment_failed": _handle_payment_failed,
        "customer.subscription.created": _handle_subscription_created,
        "customer.subscription.updated": _handle_subscription_updated,
        "customer.subscription.deleted": _handle_subscription_deleted,
        "invoice.payment_succeeded": _handle_invoice_succeeded,
        "invoice.payment_failed": _handle_invoice_failed,
    }

    handler = handlers.get(event_type)
    if handler:
        logger.info("Processing webhook event: %s", event_type)
        await handler(data, db)
    else:
        logger.info("Ignoring unhandled webhook event: %s", event_type)


async def _handle_payment_succeeded(data: dict, db: AsyncIOMotorDatabase) -> None:
    """Handle payment_intent.succeeded — confirm the order."""
    pi_id = data.get("id")
    if not pi_id:
        return

    await db.orders.update_one(
        {"stripe_payment_intent_id": pi_id, "status": "pending"},
        {"$set": {"status": "confirmed", "updated_at": _utcnow()}},
    )
    logger.info("Payment succeeded for PI %s", pi_id)


async def _handle_payment_failed(data: dict, db: AsyncIOMotorDatabase) -> None:
    """Handle payment_intent.payment_failed — mark order failed."""
    pi_id = data.get("id")
    if not pi_id:
        return

    await db.orders.update_one(
        {"stripe_payment_intent_id": pi_id},
        {"$set": {"status": "failed", "updated_at": _utcnow()}},
    )
    logger.info("Payment failed for PI %s", pi_id)


async def _handle_subscription_created(
    data: dict, db: AsyncIOMotorDatabase
) -> None:
    """Handle customer.subscription.created — save subscription record."""
    customer_id = data.get("customer")
    sub_id = data.get("id")

    # Find user by stripe_customer_id
    profile = await db.commerce_profiles.find_one(
        {"stripe_customer_id": customer_id}
    )
    if not profile:
        logger.warning("No profile found for Stripe customer %s", customer_id)
        return

    user_id = profile["user_id"]

    # Determine tier from the price
    tier = _extract_tier_from_subscription(data)

    record = SubscriptionRecord(
        user_id=user_id,
        stripe_subscription_id=sub_id,
        stripe_customer_id=customer_id,
        tier=tier,
        status=data.get("status", "active"),
        current_period_start=_ts_to_dt(data.get("current_period_start")),
        current_period_end=_ts_to_dt(data.get("current_period_end")),
        cancel_at_period_end=data.get("cancel_at_period_end", False),
    )

    await db.subscription_records.update_one(
        {"user_id": user_id},
        {"$set": record.model_dump(mode="json")},
        upsert=True,
    )

    # Sync permissions
    await _sync_permissions_from_webhook(user_id, tier)

    # Create order record for subscription
    order = Order(
        user_id=user_id,
        stripe_subscription_id=sub_id,
        order_type="subscription",
        status="confirmed",
        items=[
            OrderItem(
                item_id=f"sub_{tier}",
                item_type="subscription",
                name=f"WF {tier.title()} Subscription",
                quantity=1,
                unit_price=0,  # Price managed by Stripe
                total_price=0,
            )
        ],
    )
    await db.orders.insert_one(order.model_dump(mode="json"))

    logger.info("Subscription %s created for user %s (tier: %s)", sub_id, user_id, tier)


async def _handle_subscription_updated(
    data: dict, db: AsyncIOMotorDatabase
) -> None:
    """Handle customer.subscription.updated — update local record."""
    sub_id = data.get("id")

    update = {
        "status": data.get("status", "active"),
        "current_period_start": _ts_to_dt(data.get("current_period_start")),
        "current_period_end": _ts_to_dt(data.get("current_period_end")),
        "cancel_at_period_end": data.get("cancel_at_period_end", False),
        "updated_at": _utcnow(),
    }

    tier = _extract_tier_from_subscription(data)
    if tier:
        update["tier"] = tier

    result = await db.subscription_records.update_one(
        {"stripe_subscription_id": sub_id},
        {"$set": update},
    )

    if result.modified_count > 0 and tier:
        record = await db.subscription_records.find_one(
            {"stripe_subscription_id": sub_id}
        )
        if record:
            await _sync_permissions_from_webhook(record["user_id"], tier)

    logger.info("Subscription %s updated", sub_id)


async def _handle_subscription_deleted(
    data: dict, db: AsyncIOMotorDatabase
) -> None:
    """Handle customer.subscription.deleted — mark as expired, downgrade."""
    sub_id = data.get("id")

    result = await db.subscription_records.update_one(
        {"stripe_subscription_id": sub_id},
        {
            "$set": {
                "status": "expired",
                "cancel_at_period_end": False,
                "updated_at": _utcnow(),
            }
        },
    )

    if result.modified_count > 0:
        record = await db.subscription_records.find_one(
            {"stripe_subscription_id": sub_id}
        )
        if record:
            # Downgrade to free tier
            await _sync_permissions_from_webhook(record["user_id"], "free")

    logger.info("Subscription %s deleted (expired)", sub_id)


async def _handle_invoice_succeeded(
    data: dict, db: AsyncIOMotorDatabase
) -> None:
    """Handle invoice.payment_succeeded — update subscription period."""
    sub_id = data.get("subscription")
    if not sub_id:
        return

    # The subscription updated event will handle period updates
    logger.info("Invoice payment succeeded for subscription %s", sub_id)


async def _handle_invoice_failed(
    data: dict, db: AsyncIOMotorDatabase
) -> None:
    """Handle invoice.payment_failed — mark subscription as past_due."""
    sub_id = data.get("subscription")
    if not sub_id:
        return

    await db.subscription_records.update_one(
        {"stripe_subscription_id": sub_id},
        {"$set": {"status": "past_due", "updated_at": _utcnow()}},
    )
    logger.info("Invoice payment failed for subscription %s", sub_id)


def _extract_tier_from_subscription(data: dict) -> str:
    """Extract tier from subscription metadata or default to 'premium'."""
    metadata = data.get("metadata", {})
    tier = metadata.get("tier")
    if tier:
        return tier

    # Fallback: try to determine from items
    items = data.get("items", {}).get("data", [])
    if items:
        price_metadata = items[0].get("price", {}).get("metadata", {})
        tier = price_metadata.get("tier")
        if tier:
            return tier

    return "premium"


async def _sync_permissions_from_webhook(user_id: str, tier: str) -> None:
    """Sync permissions via httpx call to Permissions Service."""
    import httpx

    from app.config import settings

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{settings.permissions_service_url}/subscriptions/{user_id}",
                json={"tier": tier, "status": "active"},
                headers={"X-Api-Key": settings.internal_api_key},
                timeout=10,
            )
    except Exception as e:
        logger.error("Permissions sync error for %s: %s", user_id, str(e))
