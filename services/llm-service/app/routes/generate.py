import logging

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.models.generation import ImageGenRequest, TextGenRequest
from app.services import generation_service
from shared.python.auth import get_current_user
from shared.python.responses import error_response, success_response

logger = logging.getLogger("llm")
router = APIRouter(prefix="/generate", tags=["generation"])


@router.post("/text")
async def generate_text(
    request: TextGenRequest,
    current_user: dict = Depends(get_current_user),
):
    """One-shot text generation."""
    try:
        result = await generation_service.generate_text(
            prompt=request.prompt,
            config=request.config.model_dump(),
        )
        return success_response(data=result)
    except ValueError as e:
        return error_response(
            message=str(e),
            error_code="PROVIDER_UNAVAILABLE",
            status_code=503,
        )
    except Exception as e:
        logger.error("Text generation error: %s", e, exc_info=True)
        return error_response(
            message="Text generation failed",
            error_code="GENERATION_ERROR",
            status_code=500,
            detail=str(e),
        )


@router.post("/text/stream")
async def stream_text(
    request: TextGenRequest,
    current_user: dict = Depends(get_current_user),
):
    """Stream text generation via SSE."""
    return EventSourceResponse(
        generation_service.stream_text(
            prompt=request.prompt,
            config=request.config.model_dump(),
        )
    )


@router.post("/image")
async def generate_image(
    request: ImageGenRequest,
    current_user: dict = Depends(get_current_user),
):
    """Image generation."""
    style_refs = request.config.style_reference_images or []
    subject_refs = request.config.subject_reference_images or []
    logger.info(
        "Image request received — provider: %s, style_refs: %d, subject_refs: %d, aspect_ratio: %s",
        request.config.provider,
        len(style_refs),
        len(subject_refs),
        request.config.aspect_ratio,
    )
    try:
        result = await generation_service.generate_image(
            prompt=request.prompt,
            config=request.config.model_dump(),
        )
        return success_response(data=result)
    except ValueError as e:
        return error_response(
            message=str(e),
            error_code="PROVIDER_UNAVAILABLE",
            status_code=503,
        )
    except Exception as e:
        logger.error("Image generation error: %s", e, exc_info=True)
        return error_response(
            message="Image generation failed",
            error_code="GENERATION_ERROR",
            status_code=500,
            detail=str(e),
        )
