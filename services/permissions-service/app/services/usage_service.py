from datetime import datetime, timedelta, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.subscriptions import SUBSCRIPTION_TIERS


async def initialize_usage_for_tier(
    user_id: str, tier: str, db: AsyncIOMotorDatabase
) -> None:
    """Create feature usage records for all metered features in a tier."""
    tier_config = SUBSCRIPTION_TIERS.get(tier, {})
    feature_limits = tier_config.get("feature_limits", {})
    now = datetime.now(timezone.utc)
    period_end = now + timedelta(days=30)

    for feature, limit in feature_limits.items():
        existing = await db.feature_usage.find_one(
            {"user_id": user_id, "feature": feature}
        )
        if not existing:
            await db.feature_usage.insert_one({
                "user_id": user_id,
                "feature": feature,
                "used": 0,
                "limit": limit,
                "bonus": 0,
                "period_start": now,
                "period_end": period_end,
                "last_used_at": None,
            })


async def get_usage(
    user_id: str, feature: str, db: AsyncIOMotorDatabase
) -> dict[str, Any] | None:
    """Get usage stats for a user's feature. Returns None if not found."""
    doc = await db.feature_usage.find_one(
        {"user_id": user_id, "feature": feature}
    )
    if doc:
        doc.pop("_id", None)
    return doc


async def check_usage(
    user_id: str, feature: str, db: AsyncIOMotorDatabase
) -> dict[str, Any]:
    """Check if a user can use a metered feature.

    Handles period expiry reset, unlimited limits, and bonus calculation.
    Auto-initializes usage record if user has the feature in their tier but
    no usage record exists (handles features added after user creation).
    """
    doc = await db.feature_usage.find_one(
        {"user_id": user_id, "feature": feature}
    )
    if not doc:
        # Try auto-initializing from user's subscription tier
        user_perms = await db.user_permissions.find_one({"user_id": user_id})
        if user_perms:
            sub = await db.subscriptions.find_one({"user_id": user_id})
            tier = sub["tier"] if sub else "free"
            tier_config = SUBSCRIPTION_TIERS.get(tier, {})
            feature_limits = tier_config.get("feature_limits", {})
            if feature in feature_limits:
                await initialize_usage_for_tier(user_id, tier, db)
                doc = await db.feature_usage.find_one(
                    {"user_id": user_id, "feature": feature}
                )

    if not doc:
        return {
            "user_id": user_id,
            "feature": feature,
            "allowed": False,
            "used": 0,
            "limit": 0,
            "bonus": 0,
            "remaining": 0,
            "reason": "feature_not_found",
        }

    now = datetime.now(timezone.utc)

    # Check if period has expired — reset counter
    period_end = doc.get("period_end")
    if period_end:
        # Ensure timezone-aware comparison (mongomock may return naive datetimes)
        if period_end.tzinfo is None:
            period_end = period_end.replace(tzinfo=timezone.utc)
    if period_end and now > period_end:
        new_start = now
        new_end = now + timedelta(days=30)
        await db.feature_usage.update_one(
            {"user_id": user_id, "feature": feature},
            {
                "$set": {
                    "used": 0,
                    "bonus": 0,
                    "period_start": new_start,
                    "period_end": new_end,
                }
            },
        )
        doc["used"] = 0
        doc["bonus"] = 0
        doc["period_start"] = new_start
        doc["period_end"] = new_end

    used = doc.get("used", 0)
    limit = doc.get("limit", 0)
    bonus = doc.get("bonus", 0)

    # Unlimited
    if limit == -1:
        return {
            "user_id": user_id,
            "feature": feature,
            "allowed": True,
            "used": used,
            "limit": limit,
            "bonus": bonus,
            "remaining": -1,
            "reason": None,
        }

    effective_limit = limit + bonus
    remaining = max(0, effective_limit - used)
    allowed = used < effective_limit

    return {
        "user_id": user_id,
        "feature": feature,
        "allowed": allowed,
        "used": used,
        "limit": limit,
        "bonus": bonus,
        "remaining": remaining,
        "reason": None if allowed else "limit_reached",
    }


async def record_usage(
    user_id: str, feature: str, db: AsyncIOMotorDatabase
) -> dict[str, Any] | None:
    """Record one use of a feature. Returns updated usage doc."""
    now = datetime.now(timezone.utc)
    result = await db.feature_usage.find_one_and_update(
        {"user_id": user_id, "feature": feature},
        {
            "$inc": {"used": 1},
            "$set": {"last_used_at": now},
        },
        return_document=True,
    )
    if result:
        result.pop("_id", None)
    return result


async def add_bonus(
    user_id: str, feature: str, amount: int, db: AsyncIOMotorDatabase
) -> dict[str, Any] | None:
    """Add bonus uses to a feature. Returns updated usage doc."""
    result = await db.feature_usage.find_one_and_update(
        {"user_id": user_id, "feature": feature},
        {"$inc": {"bonus": amount}},
        return_document=True,
    )
    if result:
        result.pop("_id", None)
    return result


async def reset_expired_periods(db: AsyncIOMotorDatabase) -> int:
    """Reset all usage records with expired periods. Returns count of reset records."""
    now = datetime.now(timezone.utc)
    new_end = now + timedelta(days=30)

    result = await db.feature_usage.update_many(
        {"period_end": {"$lt": now}},
        {
            "$set": {
                "used": 0,
                "bonus": 0,
                "period_start": now,
                "period_end": new_end,
            }
        },
    )
    return result.modified_count
