from typing import Any

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from app.database import get_db, get_redis
from app.services import checkout_service
from shared.python.auth import get_current_user
from shared.python.responses import error_response, success_response

router = APIRouter(prefix="/checkout")


@router.post("/{user_id}/validate")
async def validate_cart(
    user_id: str,
    r: Redis = Depends(get_redis),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Validate cart is ready for checkout."""
    result = await checkout_service.validate_cart(user_id, r, db)
    if not result["valid"]:
        return error_response(
            message=result["error"],
            error_code="CART_INVALID",
            status_code=400,
        )
    return success_response(data=result)


@router.post("/{user_id}/create-payment")
async def create_payment(
    user_id: str,
    r: Redis = Depends(get_redis),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Create a Stripe PaymentIntent for the cart. Returns client_secret for mobile SDK."""
    try:
        result = await checkout_service.create_payment(user_id, r, db)
        return success_response(data=result, message="Payment created")
    except ValueError as e:
        return error_response(
            message=str(e),
            error_code="PAYMENT_ERROR",
            status_code=400,
        )


@router.post("/{user_id}/confirm")
async def confirm_payment(
    user_id: str,
    body: dict,
    r: Redis = Depends(get_redis),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Confirm payment succeeded and create order."""
    payment_intent_id = body.get("payment_intent_id")
    if not payment_intent_id:
        return error_response(
            message="payment_intent_id required",
            error_code="MISSING_FIELD",
            status_code=400,
        )

    try:
        order = await checkout_service.confirm_payment(
            user_id, payment_intent_id, r, db
        )
        return success_response(data=order, message="Order confirmed")
    except ValueError as e:
        return error_response(
            message=str(e),
            error_code="CONFIRMATION_ERROR",
            status_code=400,
        )
