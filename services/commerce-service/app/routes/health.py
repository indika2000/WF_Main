from fastapi import APIRouter, Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from app.config import settings
from app.database import get_db, get_redis
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
    r: Redis = Depends(get_redis),
):
    """Detailed health check — pings MongoDB, Redis, and checks Stripe key."""
    checks = {}

    # MongoDB
    try:
        await db.command("ping")
        checks["mongodb"] = "ok"
    except Exception as e:
        checks["mongodb"] = f"error: {str(e)}"

    # Redis
    try:
        pong = await r.ping()
        checks["redis"] = "ok" if pong else "error"
    except Exception as e:
        checks["redis"] = f"error: {str(e)}"

    # Stripe API key
    checks["stripe"] = "configured" if settings.stripe_secret_key else "not configured"

    overall = "ok" if all(
        v in ("ok", "configured") for v in checks.values()
    ) else "degraded"

    return success_response(
        data={
            "service": settings.service_name,
            "status": overall,
            "checks": checks,
        }
    )
