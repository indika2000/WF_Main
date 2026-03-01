import shutil

from fastapi import APIRouter, Request

from app.config import settings
from shared.python.responses import success_response

router = APIRouter()


@router.get("/health")
async def health_check():
    """Simple alive check."""
    return success_response(
        data={"status": "ok", "service": "image"},
        message="Healthy",
    )


@router.get("/health/detailed")
async def health_detailed(request: Request):
    """Detailed health check — pings MongoDB, checks storage."""
    checks = {"mongodb": "unknown", "storage": "unknown"}

    try:
        result = await request.app.state.db.command("ping")
        checks["mongodb"] = "ok" if result.get("ok") == 1.0 else "error"
    except Exception:
        checks["mongodb"] = "error"

    # Check storage is writable
    try:
        storage = request.app.state.storage
        await storage.save("_health_check", b"ok")
        await storage.delete("_health_check")
        checks["storage"] = "ok"
    except Exception:
        checks["storage"] = "error"

    # Disk space info
    disk_info = {}
    try:
        usage = shutil.disk_usage(settings.image_storage_path)
        disk_info = {
            "total_mb": round(usage.total / 1_048_576),
            "used_mb": round(usage.used / 1_048_576),
            "free_mb": round(usage.free / 1_048_576),
        }
    except Exception:
        pass

    all_ok = all(v == "ok" for v in checks.values())
    return success_response(
        data={
            "status": "ok" if all_ok else "degraded",
            "service": "image",
            "checks": checks,
            "disk": disk_info,
        },
        message="Healthy" if all_ok else "Degraded",
    )
