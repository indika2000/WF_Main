from typing import Any

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.models.permissions import PermissionsCreate, PermissionsUpdate
from app.services import permissions_service
from shared.python.auth import get_current_user
from shared.python.responses import error_response, success_response

router = APIRouter(prefix="/permissions")


@router.post("/{user_id}")
async def create_permissions(
    user_id: str,
    body: PermissionsCreate | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Create default permissions for a new user."""
    email = body.email if body else None
    result = await permissions_service.create_default_permissions(user_id, db, email)
    if result is None:
        return error_response(
            message="User already exists",
            error_code="USER_EXISTS",
            status_code=409,
        )
    return success_response(data=result, message="Permissions created", status_code=201)


@router.get("/{user_id}")
async def get_permissions(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Get a user's current permissions."""
    result = await permissions_service.get_permissions(user_id, db)
    if result is None:
        return error_response(
            message="User not found",
            error_code="USER_NOT_FOUND",
            status_code=404,
        )
    return success_response(data=result)


@router.patch("/{user_id}")
async def update_permissions(
    user_id: str,
    body: PermissionsUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Update specific permission flags or role."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        return error_response(
            message="No updates provided",
            error_code="INVALID_REQUEST",
            status_code=400,
        )

    result = await permissions_service.update_permissions(user_id, updates, db)
    if result is None:
        return error_response(
            message="User not found",
            error_code="USER_NOT_FOUND",
            status_code=404,
        )
    return success_response(data=result, message="Permissions updated")


@router.get("/{user_id}/check/{permission}")
async def check_permission(
    user_id: str,
    permission: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Quick boolean check for a specific permission."""
    result = await permissions_service.check_permission(user_id, permission, db)
    if result is None:
        return error_response(
            message="User not found",
            error_code="USER_NOT_FOUND",
            status_code=404,
        )
    return success_response(data=result)
