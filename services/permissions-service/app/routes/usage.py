from typing import Any

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.models.usage import BonusRequest
from app.services import usage_service
from shared.python.auth import get_current_user
from shared.python.responses import error_response, success_response

router = APIRouter(prefix="/usage")


@router.get("/{user_id}/{feature}")
async def get_usage(
    user_id: str,
    feature: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Get usage stats for a feature."""
    result = await usage_service.get_usage(user_id, feature, db)
    if result is None:
        return error_response(
            message="Usage record not found",
            error_code="NOT_FOUND",
            status_code=404,
        )
    return success_response(data=result)


@router.post("/{user_id}/{feature}/check")
async def check_usage(
    user_id: str,
    feature: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Check if a user can use a metered feature."""
    result = await usage_service.check_usage(user_id, feature, db)
    return success_response(data=result)


@router.post("/{user_id}/{feature}/record")
async def record_usage(
    user_id: str,
    feature: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Record one use of a feature."""
    result = await usage_service.record_usage(user_id, feature, db)
    if result is None:
        return error_response(
            message="Usage record not found",
            error_code="NOT_FOUND",
            status_code=404,
        )
    return success_response(data=result, message="Usage recorded")


@router.post("/{user_id}/{feature}/bonus")
async def add_bonus(
    user_id: str,
    feature: str,
    body: BonusRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Add bonus uses to a feature."""
    result = await usage_service.add_bonus(user_id, feature, body.amount, db)
    if result is None:
        return error_response(
            message="Usage record not found",
            error_code="NOT_FOUND",
            status_code=404,
        )
    return success_response(data=result, message="Bonus added")


@router.post("/reset-expired")
async def reset_expired(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Reset usage counters for all expired periods. Requires API key."""
    count = await usage_service.reset_expired_periods(db)
    return success_response(
        data={"reset_count": count},
        message=f"Reset {count} expired usage records",
    )
