"""GET /creatures/:creature_id — lookup a specific creature."""

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from shared.python.auth import get_current_user
from shared.python.responses import error_response, success_response

router = APIRouter()


@router.get("/creatures/{creature_id}")
async def get_creature(
    creature_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get a creature by its ID."""
    creature = await db.creatures.find_one(
        {"identity.creature_id": creature_id}
    )
    if not creature:
        return error_response(
            message="Creature not found",
            error_code="NOT_FOUND",
            status_code=404,
        )

    # Check if requesting user owns this creature
    ownership = await db.user_collections.find_one(
        {"user_id": user["uid"], "creature_id": creature_id}
    )

    creature.pop("_id", None)
    return success_response(
        data={
            "creature": creature,
            "is_owner": ownership is not None,
        }
    )
