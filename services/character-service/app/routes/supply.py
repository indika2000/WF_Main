"""GET /supply — current supply cap status."""

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.services.config_loader import get_config
from app.services.registry import get_supply_status
from shared.python.auth import get_current_user
from shared.python.responses import success_response

router = APIRouter()


@router.get("/supply")
async def supply_status(
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get the current supply cap status for all rarity tiers."""
    config = get_config()
    status = await get_supply_status(db, config.version)

    return success_response(
        data={
            "season": config.version,
            "tiers": status,
        }
    )
