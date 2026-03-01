from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.services import image_service
from shared.python.auth import get_current_user
from shared.python.responses import error_response, success_response

router = APIRouter(prefix="/images", tags=["user-images"])


@router.get("/user/{user_id}")
async def list_user_images(
    user_id: str,
    page: int = 1,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """List images for a user (paginated)."""
    if current_user["role"] != "service" and current_user["uid"] != user_id:
        return error_response(
            message="Not authorized to view these images",
            error_code="FORBIDDEN",
            status_code=403,
        )

    images = await image_service.list_user_images(user_id, db, page=page, limit=limit)
    return success_response(data=images)


@router.get("/user/{user_id}/{category}")
async def list_user_images_by_category(
    user_id: str,
    category: str,
    page: int = 1,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """List images for a user filtered by category."""
    if current_user["role"] != "service" and current_user["uid"] != user_id:
        return error_response(
            message="Not authorized to view these images",
            error_code="FORBIDDEN",
            status_code=403,
        )

    images = await image_service.list_user_images(
        user_id, db, category=category, page=page, limit=limit,
    )
    return success_response(data=images)
