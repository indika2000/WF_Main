import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.models.images import ImageVariant
from app.processing.image_processor import (
    get_image_dimensions,
    process_image,
    validate_image_file,
)

logger = logging.getLogger("image")


async def upload_image(
    file_data: bytes,
    filename: str,
    content_type: str,
    user_id: str,
    storage,
    db: AsyncIOMotorDatabase,
    category: str = "general",
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Upload and process an image. Returns the image record."""
    # Validate
    if len(file_data) > settings.image_max_file_size:
        raise ValueError(
            f"File too large ({len(file_data)} bytes). Max: {settings.image_max_file_size}"
        )

    if not validate_image_file(file_data, content_type):
        raise ValueError(f"Invalid image file or unsupported type: {content_type}")

    image_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    width, height = get_image_dimensions(file_data)

    # Save original
    ext = _extension_from_content_type(content_type)
    original_path = f"{user_id}/{image_id}/original.{ext}"
    await storage.save(original_path, file_data)

    # Process variants
    variants_data = process_image(file_data, preset_name=category)
    variants = {}
    for variant_name, vdata in variants_data.items():
        variant_path = f"{user_id}/{image_id}/{variant_name}.webp"
        await storage.save(variant_path, vdata["data"])
        variants[variant_name] = ImageVariant(
            width=vdata["width"],
            height=vdata["height"],
            storage_path=variant_path,
            file_size=len(vdata["data"]),
        ).model_dump()

    # Create record
    record = {
        "_id": image_id,
        "user_id": user_id,
        "category": category,
        "filename": filename,
        "content_type": content_type,
        "file_size": len(file_data),
        "width": width,
        "height": height,
        "storage_path": original_path,
        "variants": variants,
        "source": "upload",
        "metadata": metadata or {},
        "tags": tags or [],
        "created_at": now,
        "updated_at": now,
    }

    await db.images.insert_one(record)

    record["id"] = record.pop("_id")
    return record


async def get_image(
    image_id: str,
    db: AsyncIOMotorDatabase,
) -> dict[str, Any] | None:
    """Get image metadata by ID."""
    doc = await db.images.find_one({"_id": image_id})
    if doc:
        doc["id"] = doc.pop("_id")
    return doc


async def delete_image(
    image_id: str,
    user_id: str,
    storage,
    db: AsyncIOMotorDatabase,
) -> bool:
    """Delete an image and all its variants from storage and DB."""
    doc = await db.images.find_one({"_id": image_id, "user_id": user_id})
    if not doc:
        return False

    # Delete original
    try:
        await storage.delete(doc["storage_path"])
    except Exception as e:
        logger.warning("Failed to delete original %s: %s", doc["storage_path"], e)

    # Delete variants
    for variant_info in doc.get("variants", {}).values():
        try:
            path = variant_info.get("storage_path") if isinstance(variant_info, dict) else variant_info
            if path:
                await storage.delete(path)
        except Exception as e:
            logger.warning("Failed to delete variant: %s", e)

    await db.images.delete_one({"_id": image_id})
    return True


async def update_image(
    image_id: str,
    user_id: str,
    updates: dict[str, Any],
    db: AsyncIOMotorDatabase,
) -> dict[str, Any] | None:
    """Update image metadata (category, metadata, tags)."""
    allowed_fields = {"category", "metadata", "tags"}
    set_fields = {k: v for k, v in updates.items() if k in allowed_fields and v is not None}
    if not set_fields:
        return await get_image(image_id, db)

    set_fields["updated_at"] = datetime.now(timezone.utc)

    result = await db.images.update_one(
        {"_id": image_id, "user_id": user_id},
        {"$set": set_fields},
    )

    if result.matched_count == 0:
        return None

    return await get_image(image_id, db)


async def list_user_images(
    user_id: str,
    db: AsyncIOMotorDatabase,
    category: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """List images for a user, optionally filtered by category."""
    query: dict[str, Any] = {"user_id": user_id}
    if category:
        query["category"] = category

    skip = (page - 1) * limit
    cursor = db.images.find(
        query,
        {"variants": 0},  # Exclude variant details for listing
    ).sort("created_at", -1).skip(skip).limit(limit)

    results = []
    async for doc in cursor:
        doc["id"] = doc.pop("_id")
        results.append(doc)
    return results


def _extension_from_content_type(content_type: str) -> str:
    mapping = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/gif": "gif",
    }
    return mapping.get(content_type, "bin")
