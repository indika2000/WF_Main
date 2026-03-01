from fastapi import APIRouter, Request

from app.providers.factory import provider_factory
from shared.python.responses import error_response, success_response

router = APIRouter()


@router.get("/health")
async def health_check():
    """Simple alive check."""
    return success_response(
        data={"status": "ok", "service": "llm"},
        message="Healthy",
    )


@router.get("/health/detailed")
async def health_detailed(request: Request):
    """Detailed health check — pings MongoDB, checks provider availability."""
    checks = {"mongodb": "unknown", "providers": "unknown"}

    try:
        result = await request.app.state.db.command("ping")
        checks["mongodb"] = "ok" if result.get("ok") == 1.0 else "error"
    except Exception:
        checks["mongodb"] = "error"

    # Check if at least one text provider is available
    providers = provider_factory.list_providers()
    available = [p for p in providers if p["status"] == "available"]
    checks["providers"] = "ok" if available else "no_providers"

    all_ok = checks["mongodb"] == "ok" and checks["providers"] == "ok"
    return success_response(
        data={
            "status": "ok" if all_ok else "degraded",
            "service": "llm",
            "checks": checks,
            "available_providers": len(available),
        },
        message="Healthy" if all_ok else "Degraded",
    )
