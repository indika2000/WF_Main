"""Image generation job queue — schema, CRUD, and job lifecycle management.

Jobs are stored in the `image_generation_jobs` MongoDB collection and processed
by a background async worker within the character service process.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.creature import CreatureCard
from app.services.artist_loader import ArtistConfig, get_artist_registry
from app.services.prompt_builder import (
    build_card_prompt,
    build_headshot_color_prompt,
    build_headshot_pencil_prompt,
)

logger = logging.getLogger(__name__)

# Image type priorities — card must complete before headshots start
IMAGE_TYPE_PRIORITY = {
    "card": 1,
    "headshot_color": 2,
    "headshot_pencil": 3,
}

# Aspect ratios per image type
IMAGE_TYPE_ASPECT_RATIO = {
    "card": "3:4",
    "headshot_color": "1:1",
    "headshot_pencil": "1:1",
}

MAX_ATTEMPTS = 3


def _build_job(
    creature_id: str,
    image_type: str,
    artist_id: str,
    prompt: str,
    user_id: str,
    aspect_ratio: str,
) -> dict[str, Any]:
    """Build a single job document."""
    return {
        "job_id": str(uuid4()),
        "creature_id": creature_id,
        "image_type": image_type,
        "status": "pending",
        "priority": IMAGE_TYPE_PRIORITY[image_type],
        "artist_id": artist_id,
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "reference_image_id": None,  # For headshots: set when card completes
        "result_image_id": None,
        "attempts": 0,
        "max_attempts": MAX_ATTEMPTS,
        "error": None,
        "created_at": datetime.now(timezone.utc),
        "started_at": None,
        "completed_at": None,
        "requested_by": user_id,
    }


async def ensure_image_jobs(
    db: AsyncIOMotorDatabase,
    creature: CreatureCard,
    user_id: str,
) -> bool:
    """Create image generation jobs for a creature if they don't already exist.

    Returns True if new jobs were created, False if jobs/images already exist.
    """
    creature_id = creature.identity.creature_id

    # Check if non-failed jobs already exist
    existing_jobs = await db.image_generation_jobs.count_documents(
        {"creature_id": creature_id, "status": {"$ne": "failed"}}
    )
    if existing_jobs > 0:
        return False

    # Check if creature already has a card image
    creature_doc = await db.creatures.find_one(
        {"identity.creature_id": creature_id}
    )
    if creature_doc and creature_doc.get("images", {}).get("card"):
        return False

    # Assign artist
    registry = get_artist_registry()
    artist_id = registry.assign_artist(
        biome=creature.classification.biome,
        family=creature.classification.family,
        canonical_id=creature.source.canonical_id,
    )
    artist = registry.get(artist_id)
    if not artist:
        logger.error("Artist %s not found in registry", artist_id)
        return False

    # Build prompts and create jobs
    card_prompt = build_card_prompt(creature, artist)
    headshot_color_prompt = build_headshot_color_prompt(creature, artist)
    headshot_pencil_prompt = build_headshot_pencil_prompt(creature)

    jobs = [
        _build_job(
            creature_id=creature_id,
            image_type="card",
            artist_id=artist_id,
            prompt=card_prompt,
            user_id=user_id,
            aspect_ratio=IMAGE_TYPE_ASPECT_RATIO["card"],
        ),
        _build_job(
            creature_id=creature_id,
            image_type="headshot_color",
            artist_id=artist_id,
            prompt=headshot_color_prompt,
            user_id=user_id,
            aspect_ratio=IMAGE_TYPE_ASPECT_RATIO["headshot_color"],
        ),
        _build_job(
            creature_id=creature_id,
            image_type="headshot_pencil",
            artist_id=artist_id,
            prompt=headshot_pencil_prompt,
            user_id=user_id,
            aspect_ratio=IMAGE_TYPE_ASPECT_RATIO["headshot_pencil"],
        ),
    ]

    await db.image_generation_jobs.insert_many(jobs)

    # Store artist_id on the creature
    await db.creatures.update_one(
        {"identity.creature_id": creature_id},
        {"$set": {"images.artist_id": artist_id}},
    )

    logger.info(
        "Created %d image jobs for creature %s (artist: %s)",
        len(jobs),
        creature_id,
        artist_id,
    )
    return True


async def claim_next_job(db: AsyncIOMotorDatabase) -> dict[str, Any] | None:
    """Atomically claim the next pending job for processing.

    Card jobs are always eligible. Headshot jobs are only eligible when their
    reference_image_id has been set (i.e., the card image completed).

    Returns the claimed job document, or None if no work available.
    """
    now = datetime.now(timezone.utc)
    job = await db.image_generation_jobs.find_one_and_update(
        {
            "status": "pending",
            "$or": [
                {"image_type": "card"},
                {
                    "image_type": {"$ne": "card"},
                    "reference_image_id": {"$ne": None},
                },
            ],
        },
        {
            "$set": {"status": "processing", "started_at": now},
            "$inc": {"attempts": 1},
        },
        sort=[("priority", 1), ("created_at", 1)],
        return_document=True,
    )
    if job:
        job.pop("_id", None)
    return job


async def complete_job(
    db: AsyncIOMotorDatabase,
    job_id: str,
    result_image_id: str,
) -> None:
    """Mark a job as completed and update creature images."""
    now = datetime.now(timezone.utc)

    # Get the job first to know creature_id and image_type
    job = await db.image_generation_jobs.find_one({"job_id": job_id})
    if not job:
        logger.warning("Job %s not found for completion", job_id)
        return

    # Mark job completed
    await db.image_generation_jobs.update_one(
        {"job_id": job_id},
        {
            "$set": {
                "status": "completed",
                "result_image_id": result_image_id,
                "completed_at": now,
            }
        },
    )

    # Update creature's image references
    image_field = f"images.{job['image_type']}"
    await db.creatures.update_one(
        {"identity.creature_id": job["creature_id"]},
        {"$set": {image_field: result_image_id}},
    )

    # If card just completed, unlock headshot jobs by setting reference_image_id
    if job["image_type"] == "card":
        await db.image_generation_jobs.update_many(
            {
                "creature_id": job["creature_id"],
                "image_type": {"$in": ["headshot_color", "headshot_pencil"]},
            },
            {"$set": {"reference_image_id": result_image_id}},
        )

    logger.info(
        "Completed job %s (%s) for creature %s → image %s",
        job_id,
        job["image_type"],
        job["creature_id"],
        result_image_id,
    )


async def fail_job(
    db: AsyncIOMotorDatabase,
    job_id: str,
    error: str,
) -> None:
    """Handle a failed job — re-queue if attempts remain, else mark failed."""
    job = await db.image_generation_jobs.find_one({"job_id": job_id})
    if not job:
        return

    if job["attempts"] >= job["max_attempts"]:
        await db.image_generation_jobs.update_one(
            {"job_id": job_id},
            {"$set": {"status": "failed", "error": error}},
        )
        logger.error(
            "Job %s permanently failed after %d attempts: %s",
            job_id,
            job["attempts"],
            error,
        )
    else:
        # Re-queue for retry
        await db.image_generation_jobs.update_one(
            {"job_id": job_id},
            {"$set": {"status": "pending", "error": error}},
        )
        logger.warning(
            "Job %s failed (attempt %d/%d), re-queuing: %s",
            job_id,
            job["attempts"],
            job["max_attempts"],
            error,
        )


async def get_creature_image_status(
    db: AsyncIOMotorDatabase,
    creature_id: str,
) -> list[dict[str, Any]]:
    """Get the status of all image jobs for a creature."""
    cursor = db.image_generation_jobs.find(
        {"creature_id": creature_id},
        {
            "_id": 0,
            "job_id": 1,
            "image_type": 1,
            "status": 1,
            "result_image_id": 1,
            "attempts": 1,
            "error": 1,
        },
    ).sort("priority", 1)
    return await cursor.to_list(length=10)
