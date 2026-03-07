"""GET /collection — user's creature collection."""

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.services.registry import get_user_collection
from shared.python.auth import get_current_user
from shared.python.responses import success_response

router = APIRouter()


@router.get("/collection")
async def get_my_collection(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get the current user's creature collection."""
    items = await get_user_collection(db, user["uid"], skip=skip, limit=limit)

    # Clean up MongoDB _id fields
    for item in items:
        item.pop("_id", None)
        if "creature" in item and item["creature"]:
            item["creature"].pop("_id", None)

    # Get total count
    total = await db.user_collections.count_documents({"user_id": user["uid"]})

    return success_response(
        data={
            "items": items,
            "total": total,
            "skip": skip,
            "limit": limit,
        }
    )


@router.get("/collection/{user_id}")
async def get_user_collection_by_id(
    user_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get a specific user's creature collection (public view)."""
    items = await get_user_collection(db, user_id, skip=skip, limit=limit)

    for item in items:
        item.pop("_id", None)
        if "creature" in item and item["creature"]:
            item["creature"].pop("_id", None)

    total = await db.user_collections.count_documents({"user_id": user_id})

    return success_response(
        data={
            "items": items,
            "total": total,
            "skip": skip,
            "limit": limit,
        }
    )
