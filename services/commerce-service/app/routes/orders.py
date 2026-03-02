from typing import Any

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from shared.python.auth import get_current_user
from shared.python.responses import error_response, success_response

router = APIRouter(prefix="/orders")


@router.get("/{user_id}")
async def list_orders(
    user_id: str,
    page: int = 1,
    limit: int = 20,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """List a user's orders (paginated, newest first)."""
    skip = (page - 1) * limit
    cursor = (
        db.orders.find({"user_id": user_id}, {"_id": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    orders = await cursor.to_list(length=limit)
    total = await db.orders.count_documents({"user_id": user_id})

    return success_response(
        data={
            "orders": orders,
            "page": page,
            "limit": limit,
            "total": total,
        }
    )


@router.get("/{user_id}/{order_id}")
async def get_order(
    user_id: str,
    order_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Get a specific order by ID."""
    order = await db.orders.find_one(
        {"order_id": order_id, "user_id": user_id}, {"_id": 0}
    )
    if order is None:
        return error_response(
            message="Order not found",
            error_code="NOT_FOUND",
            status_code=404,
        )
    return success_response(data=order)
