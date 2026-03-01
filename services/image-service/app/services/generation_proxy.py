import base64
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.models.images import ImageVariant
from app.processing.image_processor import get_image_dimensions, process_image

logger = logging.getLogger("image")


async def generate_image(
    prompt: str,
    user_id: str,
    storage,
    db: AsyncIOMotorDatabase,
    provider: str | None = None,
    size: str = "1024x1024",
    quality: str = "standard",
    n: int = 1,
    category: str = "ai_generated",
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Generate images via LLM Service and save to storage.

    Calls the LLM service's /generate/image endpoint, then saves
    each generated image with processed variants.
    """
    # Call LLM service
    payload: dict[str, Any] = {
        "prompt": prompt,
        "config": {
            "size": size,
            "quality": quality,
            "n": n,
        },
    }
    if provider:
        payload["config"]["provider"] = provider

    api_key = os.environ.get("INTERNAL_API_KEY", "")
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{settings.llm_service_url}/generate/image",
            json=payload,
            headers={"X-Api-Key": api_key},
        )

    if response.status_code != 200:
        raise ValueError(f"LLM service image generation failed: {response.text}")

    result = response.json()
    if not result.get("success"):
        raise ValueError(f"LLM service error: {result.get('message', 'Unknown error')}")

    generated_images = result["data"]["images"]
    now = datetime.now(timezone.utc)
    saved_records = []

    for img_data in generated_images:
        image_bytes = base64.b64decode(img_data["data"])
        image_id = str(uuid.uuid4())
        fmt = img_data.get("format", "png")

        width, height = get_image_dimensions(image_bytes)

        # Save original
        original_path = f"{user_id}/{image_id}/original.{fmt}"
        await storage.save(original_path, image_bytes)

        # Process variants
        variants_data = process_image(image_bytes, preset_name=category)
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

        record = {
            "_id": image_id,
            "user_id": user_id,
            "category": category,
            "filename": f"generated-{image_id}.{fmt}",
            "content_type": f"image/{fmt}",
            "file_size": len(image_bytes),
            "width": width,
            "height": height,
            "storage_path": original_path,
            "variants": variants,
            "source": "ai_generated",
            "metadata": {
                **(metadata or {}),
                "prompt": prompt,
                "provider": result["data"].get("provider"),
                "model": result["data"].get("model"),
            },
            "tags": tags or [],
            "created_at": now,
            "updated_at": now,
        }

        await db.images.insert_one(record)
        record["id"] = record.pop("_id")
        saved_records.append(record)

    return saved_records
