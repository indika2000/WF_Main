import logging

from fastapi import APIRouter, Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.models.images import GenerateRequest
from app.services import generation_proxy
from shared.python.auth import get_current_user
from shared.python.responses import error_response, success_response

logger = logging.getLogger("image")
router = APIRouter(prefix="/images", tags=["generation"])


@router.post("/generate")
async def generate_image(
    request_body: GenerateRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Generate images via AI and save to storage."""
    try:
        records = await generation_proxy.generate_image(
            prompt=request_body.prompt,
            user_id=current_user["uid"],
            storage=request.app.state.storage,
            db=db,
            provider=request_body.provider,
            size=request_body.size,
            quality=request_body.quality,
            n=request_body.n,
            category=request_body.category,
            tags=request_body.tags,
            metadata=request_body.metadata,
        )
        return success_response(data=records, status_code=201)
    except ValueError as e:
        return error_response(
            message=str(e),
            error_code="GENERATION_ERROR",
            status_code=400,
        )
    except Exception as e:
        logger.error("Image generation error: %s", e, exc_info=True)
        return error_response(
            message="Image generation failed",
            error_code="GENERATION_ERROR",
            status_code=500,
            detail=str(e),
        )
