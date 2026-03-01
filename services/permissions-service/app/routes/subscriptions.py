from typing import Any

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.models.subscriptions import SUBSCRIPTION_TIERS, SubscriptionCreate
from app.services import permissions_service, subscription_service
from shared.python.auth import get_current_user
from shared.python.responses import error_response, success_response

router = APIRouter(prefix="/subscriptions")


@router.get("/tiers", name="list_tiers")
async def list_tiers():
    """List all available subscription tiers."""
    return success_response(data=subscription_service.get_tiers())


@router.post("/{user_id}")
async def create_or_update_subscription(
    user_id: str,
    body: SubscriptionCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Create or update a user's subscription. Triggers permission sync."""
    if body.tier not in SUBSCRIPTION_TIERS:
        return error_response(
            message=f"Invalid tier: {body.tier}",
            error_code="INVALID_TIER",
            status_code=400,
        )

    result = await subscription_service.create_subscription(user_id, body, db)
    return success_response(data=result, message="Subscription updated")


@router.get("/{user_id}")
async def get_subscription(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Get a user's current subscription."""
    result = await subscription_service.get_subscription(user_id, db)
    if result is None:
        return error_response(
            message="Subscription not found",
            error_code="USER_NOT_FOUND",
            status_code=404,
        )
    return success_response(data=result)


@router.post("/{user_id}/sync")
async def sync_permissions(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Force sync permissions to match current subscription tier."""
    sub = await subscription_service.get_subscription(user_id, db)
    if sub is None:
        return error_response(
            message="Subscription not found",
            error_code="USER_NOT_FOUND",
            status_code=404,
        )

    result = await permissions_service.sync_permissions_to_tier(
        user_id, sub["tier"], db
    )
    return success_response(data=result, message="Permissions synced")
