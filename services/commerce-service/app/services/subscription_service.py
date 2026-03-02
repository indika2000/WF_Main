import logging
from datetime import datetime, timezone

import httpx
import stripe
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.models.orders import SUBSCRIPTION_TIERS, SubscriptionRecord

logger = logging.getLogger("commerce")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_price_id(tier: str) -> str:
    """Map tier name to Stripe Price ID from config."""
    prices = {
        "premium": settings.stripe_price_premium,
        "ultra": settings.stripe_price_ultra,
    }
    price_id = prices.get(tier)
    if not price_id:
        raise ValueError(f"No price configured for tier: {tier}")
    return price_id


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


async def _sync_permissions(user_id: str, tier: str, status: str = "active") -> None:
    """Call Permissions Service to sync user permissions after subscription change."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.permissions_service_url}/subscriptions/{user_id}",
                json={"tier": tier, "status": status},
                headers={"X-Api-Key": settings.internal_api_key},
                timeout=10,
            )
            if response.status_code >= 400:
                logger.error(
                    "Failed to sync permissions for %s: %s",
                    user_id,
                    response.text,
                )
    except Exception as e:
        logger.error("Permissions sync error for %s: %s", user_id, str(e))


async def get_subscription(
    user_id: str, db: AsyncIOMotorDatabase
) -> dict | None:
    """Get a user's current subscription record."""
    record = await db.subscription_records.find_one(
        {"user_id": user_id}, {"_id": 0}
    )
    return record


async def create_subscription(
    user_id: str, tier: str, db: AsyncIOMotorDatabase
) -> dict:
    """Create a new Stripe subscription for the user."""
    if tier not in SUBSCRIPTION_TIERS:
        raise ValueError(f"Invalid tier: {tier}")

    # Check for existing active subscription
    existing = await db.subscription_records.find_one(
        {"user_id": user_id, "status": {"$in": ["active", "past_due"]}}
    )
    if existing:
        raise ValueError("User already has an active subscription")

    customer_id = await _get_or_create_customer(user_id, db)
    price_id = _get_price_id(tier)

    subscription = stripe.Subscription.create(
        customer=customer_id,
        items=[{"price": price_id}],
        payment_behavior="default_incomplete",
        expand=["latest_invoice.payment_intent"],
    )

    # Extract client secret for mobile SDK payment confirmation
    client_secret = None
    if (
        subscription.latest_invoice
        and subscription.latest_invoice.payment_intent
    ):
        client_secret = subscription.latest_invoice.payment_intent.client_secret

    # Save subscription record (status will be updated by webhook)
    record = SubscriptionRecord(
        user_id=user_id,
        stripe_subscription_id=subscription.id,
        stripe_customer_id=customer_id,
        tier=tier,
        status="pending",
    )

    await db.subscription_records.update_one(
        {"user_id": user_id},
        {"$set": record.model_dump(mode="json")},
        upsert=True,
    )

    return {
        "subscription_id": subscription.id,
        "client_secret": client_secret,
        "status": subscription.status,
    }


async def cancel_subscription(
    user_id: str, db: AsyncIOMotorDatabase
) -> dict:
    """Cancel subscription at period end."""
    record = await db.subscription_records.find_one({"user_id": user_id})
    if not record:
        raise ValueError("No subscription found")

    stripe.Subscription.modify(
        record["stripe_subscription_id"],
        cancel_at_period_end=True,
    )

    await db.subscription_records.update_one(
        {"user_id": user_id},
        {"$set": {"cancel_at_period_end": True, "updated_at": _utcnow()}},
    )

    return {
        "subscription_id": record["stripe_subscription_id"],
        "cancel_at_period_end": True,
        "current_period_end": record.get("current_period_end"),
    }


async def reactivate_subscription(
    user_id: str, db: AsyncIOMotorDatabase
) -> dict:
    """Reactivate a subscription that was scheduled for cancellation."""
    record = await db.subscription_records.find_one({"user_id": user_id})
    if not record:
        raise ValueError("No subscription found")

    if not record.get("cancel_at_period_end"):
        raise ValueError("Subscription is not scheduled for cancellation")

    stripe.Subscription.modify(
        record["stripe_subscription_id"],
        cancel_at_period_end=False,
    )

    await db.subscription_records.update_one(
        {"user_id": user_id},
        {"$set": {"cancel_at_period_end": False, "updated_at": _utcnow()}},
    )

    return {
        "subscription_id": record["stripe_subscription_id"],
        "cancel_at_period_end": False,
    }


async def change_tier(
    user_id: str, new_tier: str, db: AsyncIOMotorDatabase
) -> dict:
    """Change subscription tier (upgrade/downgrade)."""
    if new_tier not in SUBSCRIPTION_TIERS:
        raise ValueError(f"Invalid tier: {new_tier}")

    record = await db.subscription_records.find_one({"user_id": user_id})
    if not record:
        raise ValueError("No subscription found")

    if record.get("tier") == new_tier:
        raise ValueError("Already on this tier")

    new_price_id = _get_price_id(new_tier)

    # Get the subscription to find the current item
    sub = stripe.Subscription.retrieve(record["stripe_subscription_id"])

    stripe.Subscription.modify(
        record["stripe_subscription_id"],
        items=[
            {
                "id": sub["items"]["data"][0]["id"],
                "price": new_price_id,
            }
        ],
    )

    await db.subscription_records.update_one(
        {"user_id": user_id},
        {"$set": {"tier": new_tier, "updated_at": _utcnow()}},
    )

    # Sync permissions for new tier
    await _sync_permissions(user_id, new_tier)

    return {
        "subscription_id": record["stripe_subscription_id"],
        "tier": new_tier,
    }
