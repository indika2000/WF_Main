import logging

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.models.images import ImageUpdate
from app.services import image_service
from shared.python.auth import get_current_user
from shared.python.responses import error_response, success_response

logger = logging.getLogger("image")
router = APIRouter(prefix="/images", tags=["images"])


@router.post("/upload")
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    category: str = Form("general"),
    tags: str = Form(""),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Upload an image file with optional category and tags."""
    try:
        file_data = await file.read()
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

        record = await image_service.upload_image(
            file_data=file_data,
            filename=file.filename or "unknown",
            content_type=file.content_type or "application/octet-stream",
            user_id=current_user["uid"],
            storage=request.app.state.storage,
            db=db,
            category=category,
            tags=tag_list,
        )
        return success_response(data=record, status_code=201)
    except ValueError as e:
        return error_response(
            message=str(e),
            error_code="UPLOAD_ERROR",
            status_code=400,
        )
    except Exception as e:
        logger.error("Upload error: %s", e, exc_info=True)
        return error_response(
            message="Upload failed",
            error_code="UPLOAD_ERROR",
            status_code=500,
            detail=str(e),
        )


@router.get("/{image_id}")
async def get_image_metadata(
    image_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get image metadata."""
    record = await image_service.get_image(image_id, db)
    if not record:
        return error_response(
            message="Image not found",
            error_code="NOT_FOUND",
            status_code=404,
        )
    return success_response(data=record)


@router.get("/{image_id}/file")
async def serve_image_file(
    image_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Serve the original image file."""
    record = await image_service.get_image(image_id, db)
    if not record:
        return error_response(
            message="Image not found",
            error_code="NOT_FOUND",
            status_code=404,
        )

    try:
        data = await request.app.state.storage.load(record["storage_path"])
        return Response(
            content=data,
            media_type=record["content_type"],
            headers={"Cache-Control": "public, max-age=86400"},
        )
    except Exception as e:
        logger.error("Failed to serve image %s: %s", image_id, e)
        return error_response(
            message="Failed to serve image",
            error_code="STORAGE_ERROR",
            status_code=500,
        )


@router.get("/{image_id}/file/{variant}")
async def serve_image_variant(
    image_id: str,
    variant: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Serve a processed image variant (thumb, medium, large)."""
    record = await image_service.get_image(image_id, db)
    if not record:
        return error_response(
            message="Image not found",
            error_code="NOT_FOUND",
            status_code=404,
        )

    variants = record.get("variants", {})
    if variant not in variants:
        return error_response(
            message=f"Variant '{variant}' not found",
            error_code="NOT_FOUND",
            status_code=404,
        )

    try:
        variant_path = variants[variant]["storage_path"]
        data = await request.app.state.storage.load(variant_path)
        return Response(
            content=data,
            media_type="image/webp",
            headers={"Cache-Control": "public, max-age=86400"},
        )
    except Exception as e:
        logger.error("Failed to serve variant %s/%s: %s", image_id, variant, e)
        return error_response(
            message="Failed to serve variant",
            error_code="STORAGE_ERROR",
            status_code=500,
        )


@router.delete("/{image_id}")
async def delete_image(
    image_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Delete an image and all its variants."""
    deleted = await image_service.delete_image(
        image_id, current_user["uid"], request.app.state.storage, db,
    )
    if not deleted:
        return error_response(
            message="Image not found",
            error_code="NOT_FOUND",
            status_code=404,
        )
    return success_response(message="Image deleted")


@router.patch("/{image_id}")
async def update_image(
    image_id: str,
    updates: ImageUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Update image metadata."""
    record = await image_service.update_image(
        image_id, current_user["uid"], updates.model_dump(exclude_none=True), db,
    )
    if not record:
        return error_response(
            message="Image not found",
            error_code="NOT_FOUND",
            status_code=404,
        )
    return success_response(data=record)
