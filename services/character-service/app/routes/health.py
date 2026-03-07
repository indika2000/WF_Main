from fastapi import APIRouter, Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.database import get_db
from shared.python.responses import success_response

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check."""
    return success_response(
        data={"service": settings.service_name, "status": "ok"}
    )


@router.get("/health/detailed")
async def health_detailed(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Detailed health check — pings MongoDB and checks generation config."""
    checks = {}

    # MongoDB
    try:
        await db.command("ping")
        checks["mongodb"] = "ok"
    except Exception as e:
        checks["mongodb"] = f"error: {str(e)}"

    # Generation config
    try:
        from app.services.config_loader import get_config

        config = get_config()
        checks["generation_config"] = f"v{config.version} ({len(config.biomes)} biomes, {len(config._species_ids)} species)"
    except Exception as e:
        checks["generation_config"] = f"error: {str(e)}"

    overall = "ok" if all(
        not v.startswith("error") for v in checks.values()
    ) else "degraded"

    return success_response(
        data={
            "service": settings.service_name,
            "status": overall,
            "checks": checks,
        }
    )
