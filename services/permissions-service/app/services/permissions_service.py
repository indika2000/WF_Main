from datetime import datetime, timedelta, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.permissions import DEFAULT_PERMISSIONS, UserPermissions
from app.models.subscriptions import SUBSCRIPTION_TIERS


async def create_default_permissions(
    user_id: str, db: AsyncIOMotorDatabase, email: str | None = None
) -> dict[str, Any]:
    """Create default permissions for a new user.

    Also creates a free subscription and initial feature usage records.
    Returns the created permissions document.
    """
    # Check if user already exists
    existing = await db.user_permissions.find_one({"user_id": user_id})
    if existing:
        return None  # Caller should handle 409

    perms = UserPermissions(user_id=user_id, email=email)

    # Apply free tier permissions
    free_tier = SUBSCRIPTION_TIERS["free"]
    for key, value in free_tier["permissions"].items():
        perms.permissions[key] = value

    doc = perms.model_dump()
    await db.user_permissions.insert_one(doc)

    # Create free subscription
    from app.services.subscription_service import create_subscription
    from app.models.subscriptions import SubscriptionCreate

    await create_subscription(
        user_id, SubscriptionCreate(tier="free"), db
    )

    # Initialize feature usage records
    from app.services.usage_service import initialize_usage_for_tier

    await initialize_usage_for_tier(user_id, "free", db)

    # Remove MongoDB _id before returning
    doc.pop("_id", None)
    return doc


async def get_permissions(
    user_id: str, db: AsyncIOMotorDatabase
) -> dict[str, Any] | None:
    """Get a user's permissions. Returns None if not found."""
    doc = await db.user_permissions.find_one({"user_id": user_id})
    if doc:
        doc.pop("_id", None)
    return doc


async def update_permissions(
    user_id: str, updates: dict[str, Any], db: AsyncIOMotorDatabase
) -> dict[str, Any] | None:
    """Partial update of a user's permissions. Returns updated doc or None."""
    # Build the $set dict
    set_dict: dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}

    if "role" in updates and updates["role"] is not None:
        set_dict["role"] = updates["role"]
    if "is_premium" in updates and updates["is_premium"] is not None:
        set_dict["is_premium"] = updates["is_premium"]
    if "is_admin" in updates and updates["is_admin"] is not None:
        set_dict["is_admin"] = updates["is_admin"]
    if "permissions" in updates and updates["permissions"] is not None:
        for key, value in updates["permissions"].items():
            set_dict[f"permissions.{key}"] = value

    result = await db.user_permissions.find_one_and_update(
        {"user_id": user_id},
        {"$set": set_dict},
        return_document=True,
    )
    if result:
        result.pop("_id", None)
    return result


async def check_permission(
    user_id: str, permission: str, db: AsyncIOMotorDatabase
) -> dict[str, Any] | None:
    """Check a single permission flag for a user. Returns None if user not found."""
    doc = await db.user_permissions.find_one({"user_id": user_id})
    if not doc:
        return None

    allowed = doc.get("permissions", {}).get(permission, False)
    return {
        "user_id": user_id,
        "permission": permission,
        "allowed": allowed,
    }


async def sync_permissions_to_tier(
    user_id: str, tier: str, db: AsyncIOMotorDatabase
) -> dict[str, Any] | None:
    """Sync a user's permissions and usage limits to match their subscription tier."""
    tier_config = SUBSCRIPTION_TIERS.get(tier)
    if not tier_config:
        return None

    set_dict: dict[str, Any] = {
        "is_premium": tier != "free",
        "updated_at": datetime.now(timezone.utc),
    }
    for key, value in tier_config["permissions"].items():
        set_dict[f"permissions.{key}"] = value

    result = await db.user_permissions.find_one_and_update(
        {"user_id": user_id},
        {"$set": set_dict},
        return_document=True,
    )

    # Update feature usage limits
    for feature, limit in tier_config.get("feature_limits", {}).items():
        await db.feature_usage.update_one(
            {"user_id": user_id, "feature": feature},
            {"$set": {"limit": limit}},
        )

    if result:
        result.pop("_id", None)
    return result
