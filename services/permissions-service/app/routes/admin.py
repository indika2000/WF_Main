from typing import Any

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from shared.python.auth import require_role
from shared.python.responses import error_response, success_response

router = APIRouter(prefix="/admin")


@router.get("/users")
async def list_users(
    role: str | None = Query(None),
    tier: str | None = Query(None),
    is_premium: bool | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict[str, Any] = Depends(require_role("admin")),
):
    """List users with optional filters. Admin only."""
    query: dict[str, Any] = {}
    if role is not None:
        query["role"] = role
    if is_premium is not None:
        query["is_premium"] = is_premium

    cursor = db.user_permissions.find(query, {"_id": 0}).skip(skip).limit(limit)
    users = await cursor.to_list(length=limit)

    # If tier filter, join with subscriptions
    if tier is not None:
        user_ids = [u["user_id"] for u in users]
        sub_cursor = db.subscriptions.find(
            {"user_id": {"$in": user_ids}, "tier": tier}, {"_id": 0}
        )
        subs = await sub_cursor.to_list(length=limit)
        sub_user_ids = {s["user_id"] for s in subs}
        users = [u for u in users if u["user_id"] in sub_user_ids]

    total = await db.user_permissions.count_documents(query)

    return success_response(
        data={"users": users, "total": total, "skip": skip, "limit": limit}
    )


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict[str, Any] = Depends(require_role("admin")),
):
    """Change a user's role. Admin only."""
    valid_roles = {"user", "admin", "moderator"}
    if role not in valid_roles:
        return error_response(
            message=f"Invalid role. Must be one of: {', '.join(valid_roles)}",
            error_code="INVALID_ROLE",
            status_code=400,
        )

    result = await db.user_permissions.find_one_and_update(
        {"user_id": user_id},
        {"$set": {"role": role, "is_admin": role == "admin"}},
        return_document=True,
    )
    if result is None:
        return error_response(
            message="User not found",
            error_code="USER_NOT_FOUND",
            status_code=404,
        )

    result.pop("_id", None)
    return success_response(data=result, message=f"Role updated to {role}")
