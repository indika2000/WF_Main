from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.subscriptions import SUBSCRIPTION_TIERS, Subscription, SubscriptionCreate


async def create_subscription(
    user_id: str, data: SubscriptionCreate, db: AsyncIOMotorDatabase
) -> dict[str, Any]:
    """Create or update a user's subscription. Triggers permission sync."""
    now = datetime.now(timezone.utc)

    existing = await db.subscriptions.find_one({"user_id": user_id})
    if existing:
        # Update existing subscription
        set_dict = {
            "tier": data.tier,
            "status": data.status,
            "updated_at": now,
        }
        if data.stripe_subscription_id is not None:
            set_dict["stripe_subscription_id"] = data.stripe_subscription_id
        if data.stripe_customer_id is not None:
            set_dict["stripe_customer_id"] = data.stripe_customer_id
        if data.current_period_start is not None:
            set_dict["current_period_start"] = data.current_period_start
        if data.current_period_end is not None:
            set_dict["current_period_end"] = data.current_period_end

        result = await db.subscriptions.find_one_and_update(
            {"user_id": user_id},
            {"$set": set_dict},
            return_document=True,
        )
    else:
        # Create new subscription
        sub = Subscription(
            user_id=user_id,
            tier=data.tier,
            status=data.status,
            stripe_subscription_id=data.stripe_subscription_id,
            stripe_customer_id=data.stripe_customer_id,
            current_period_start=data.current_period_start,
            current_period_end=data.current_period_end,
        )
        doc = sub.model_dump()
        await db.subscriptions.insert_one(doc)
        result = doc

    # Sync permissions to match new tier
    from app.services.permissions_service import sync_permissions_to_tier

    await sync_permissions_to_tier(user_id, data.tier, db)

    if result:
        result.pop("_id", None)
    return result


async def get_subscription(
    user_id: str, db: AsyncIOMotorDatabase
) -> dict[str, Any] | None:
    """Get a user's current subscription. Returns None if not found."""
    doc = await db.subscriptions.find_one({"user_id": user_id})
    if doc:
        doc.pop("_id", None)
    return doc


def get_tiers() -> dict:
    """Return all available subscription tier configurations."""
    return SUBSCRIPTION_TIERS
