import logging

from fastapi import APIRouter, Depends

from app.services import provider_service
from shared.python.auth import get_current_user
from shared.python.responses import error_response, success_response

logger = logging.getLogger("llm")
router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("")
async def list_providers(
    current_user: dict = Depends(get_current_user),
):
    """List all providers with their capabilities and status."""
    providers = provider_service.list_providers()
    return success_response(data=providers)


@router.get("/{provider_name}/status")
async def check_provider_status(
    provider_name: str,
    current_user: dict = Depends(get_current_user),
):
    """Check if a specific provider is available and responsive."""
    try:
        status = await provider_service.check_provider_status(provider_name)
        return success_response(data=status)
    except Exception as e:
        logger.error("Provider status check error: %s", e, exc_info=True)
        return error_response(
            message="Status check failed",
            error_code="STATUS_CHECK_ERROR",
            status_code=500,
            detail=str(e),
        )
