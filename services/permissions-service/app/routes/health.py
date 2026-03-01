from fastapi import APIRouter, Request

from shared.python.responses import success_response, error_response

router = APIRouter()


@router.get("/health")
async def health_check():
    """Simple alive check."""
    return success_response(
        data={"status": "ok", "service": "permissions"},
        message="Healthy",
    )


@router.get("/health/detailed")
async def health_detailed(request: Request):
    """Detailed health check — pings MongoDB."""
    checks = {"mongodb": "unknown"}

    try:
        result = await request.app.state.db.command("ping")
        checks["mongodb"] = "ok" if result.get("ok") == 1.0 else "error"
    except Exception:
        checks["mongodb"] = "error"

    all_ok = all(v == "ok" for v in checks.values())
    return success_response(
        data={
            "status": "ok" if all_ok else "degraded",
            "service": "permissions",
            "checks": checks,
        },
        message="Healthy" if all_ok else "Degraded",
    )
