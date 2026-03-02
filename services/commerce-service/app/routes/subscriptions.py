from typing import Any

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.models.orders import SUBSCRIPTION_TIERS, SubscriptionCreate, TierChange
from app.services import subscription_service
from shared.python.auth import get_current_user
from shared.python.responses import error_response, success_response

router = APIRouter(prefix="/subscriptions")


@router.get("/{user_id}")
async def get_subscription(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Get a user's current subscription."""
    record = await subscription_service.get_subscription(user_id, db)
    if record is None:
        return error_response(
            message="No subscription found",
            error_code="NOT_FOUND",
            status_code=404,
        )
    return success_response(data=record)


@router.post("/{user_id}/create")
async def create_subscription(
    user_id: str,
    body: SubscriptionCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Create a new subscription. Returns client_secret for mobile SDK."""
    if body.tier not in SUBSCRIPTION_TIERS:
        return error_response(
            message=f"Invalid tier: {body.tier}. Must be one of: {', '.join(SUBSCRIPTION_TIERS)}",
            error_code="INVALID_TIER",
            status_code=400,
        )

    try:
        result = await subscription_service.create_subscription(
            user_id, body.tier, db
        )
        return success_response(data=result, message="Subscription created")
    except ValueError as e:
        return error_response(
            message=str(e),
            error_code="SUBSCRIPTION_ERROR",
            status_code=400,
        )


@router.post("/{user_id}/cancel")
async def cancel_subscription(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Cancel subscription at end of current period."""
    try:
        result = await subscription_service.cancel_subscription(user_id, db)
        return success_response(data=result, message="Subscription will cancel at period end")
    except ValueError as e:
        return error_response(
            message=str(e),
            error_code="CANCEL_ERROR",
            status_code=400,
        )


@router.post("/{user_id}/reactivate")
async def reactivate_subscription(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Reactivate a subscription that was scheduled for cancellation."""
    try:
        result = await subscription_service.reactivate_subscription(user_id, db)
        return success_response(data=result, message="Subscription reactivated")
    except ValueError as e:
        return error_response(
            message=str(e),
            error_code="REACTIVATE_ERROR",
            status_code=400,
        )


@router.post("/{user_id}/change-tier")
async def change_tier(
    user_id: str,
    body: TierChange,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Change subscription tier (upgrade/downgrade)."""
    if body.new_tier not in SUBSCRIPTION_TIERS:
        return error_response(
            message=f"Invalid tier: {body.new_tier}",
            error_code="INVALID_TIER",
            status_code=400,
        )

    try:
        result = await subscription_service.change_tier(
            user_id, body.new_tier, db
        )
        return success_response(data=result, message="Tier changed")
    except ValueError as e:
        return error_response(
            message=str(e),
            error_code="TIER_CHANGE_ERROR",
            status_code=400,
        )
