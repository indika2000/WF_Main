"""Background image generation worker.

Runs as an asyncio task within the character service process. Polls the
image_generation_jobs collection and processes jobs using the LLM service
(Gemini Imagen) and Image service (storage).
"""

import asyncio
import base64  # still needed for decoding the LLM response
import logging
from typing import Any

import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.services.image_jobs import claim_next_job, complete_job, fail_job

logger = logging.getLogger(__name__)

# Module-level state
_worker_task: asyncio.Task | None = None
_sse_subscribers: dict[str, list[asyncio.Queue]] = {}


def get_sse_subscribers() -> dict[str, list[asyncio.Queue]]:
    """Get the SSE subscriber registry for image readiness events."""
    return _sse_subscribers


def subscribe_creature_images(creature_id: str) -> asyncio.Queue:
    """Subscribe to image readiness events for a creature. Returns an event queue."""
    queue: asyncio.Queue = asyncio.Queue()
    if creature_id not in _sse_subscribers:
        _sse_subscribers[creature_id] = []
    _sse_subscribers[creature_id].append(queue)
    return queue


def unsubscribe_creature_images(creature_id: str, queue: asyncio.Queue) -> None:
    """Remove a subscriber queue."""
    if creature_id in _sse_subscribers:
        try:
            _sse_subscribers[creature_id].remove(queue)
        except ValueError:
            pass
        if not _sse_subscribers[creature_id]:
            del _sse_subscribers[creature_id]


async def notify_image_ready(
    creature_id: str, image_type: str, image_id: str
) -> None:
    """Push an image readiness event to all SSE subscribers for this creature."""
    queues = _sse_subscribers.get(creature_id, [])
    event = {
        "event": "image_ready",
        "creature_id": creature_id,
        "image_type": image_type,
        "image_id": image_id,
    }
    for queue in queues:
        await queue.put(event)

    # If all 3 images are done, send a completion event
    if image_type in ("headshot_color", "headshot_pencil"):
        # Check if this was the last image
        # (simplified: just send done after each, client tracks)
        pass


async def _generate_image_via_llm(
    prompt: str,
    aspect_ratio: str,
    artist_id: str,
) -> bytes:
    """Call the LLM service to generate an image. Returns raw PNG bytes.

    Note: style_reference_images and subject_reference_images are NOT sent —
    these trigger the Imagen edit_image API which requires Vertex AI auth,
    not the standard google-genai client. Style is conveyed via the text
    prompt's style_directive instead.
    """
    config: dict[str, Any] = {
        "provider": "gemini",
        "n": 1,
        "aspect_ratio": aspect_ratio,
        "person_generation": "DONT_ALLOW",
    }

    # Log full details of what we're sending
    logger.info(
        "=== LLM IMAGE REQUEST ===\n"
        "  Artist: %s\n"
        "  Aspect ratio: %s\n"
        "  Prompt:\n%s\n"
        "=========================",
        artist_id,
        aspect_ratio,
        prompt,
    )

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.llm_service_url}/generate/image",
            json={"prompt": prompt, "config": config},
            headers={"X-Api-Key": settings.internal_api_key},
        )
        response.raise_for_status()

    data = response.json()
    if not data.get("success") or not data.get("data", {}).get("images"):
        raise RuntimeError(f"LLM image generation failed: {data}")

    logger.info(
        "=== LLM IMAGE RESPONSE ===\n"
        "  Success: %s\n"
        "  Images returned: %d\n"
        "  Provider: %s\n"
        "==========================",
        data.get("success"),
        len(data.get("data", {}).get("images", [])),
        data.get("data", {}).get("provider", "unknown"),
    )

    image_b64 = data["data"]["images"][0]["data"]
    return base64.b64decode(image_b64)


async def _store_image(
    image_bytes: bytes,
    creature_id: str,
    image_type: str,
) -> str:
    """Upload an image to the image service. Returns the image_id."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.image_service_url}/images/upload",
            files={"file": (f"{creature_id}_{image_type}.png", image_bytes, "image/png")},
            data={
                "category": "creature_art",
                "user_id": "_system",
            },
            headers={"X-Api-Key": settings.internal_api_key},
        )
        response.raise_for_status()

    data = response.json()
    if not data.get("success"):
        raise RuntimeError(f"Image storage failed: {data}")

    return data["data"]["id"]


async def _process_job(db: AsyncIOMotorDatabase, job: dict[str, Any]) -> None:
    """Process a single image generation job."""
    creature_id = job["creature_id"]
    image_type = job["image_type"]
    job_id = job["job_id"]

    logger.info(
        "Processing job %s: %s for %s (attempt %d)",
        job_id,
        image_type,
        creature_id,
        job["attempts"],
    )

    # Generate the image
    image_bytes = await _generate_image_via_llm(
        prompt=job["prompt"],
        aspect_ratio=job.get("aspect_ratio", "1:1"),
        artist_id=job["artist_id"],
    )

    # Store the image
    image_id = await _store_image(image_bytes, creature_id, image_type)

    # Mark job completed and update creature
    await complete_job(db, job_id, image_id)

    # Notify SSE subscribers
    await notify_image_ready(creature_id, image_type, image_id)

    logger.info(
        "Completed job %s: %s for %s → %s",
        job_id,
        image_type,
        creature_id,
        image_id,
    )


async def _worker_loop(db: AsyncIOMotorDatabase) -> None:
    """Main worker loop — claims and processes jobs with concurrency control."""
    semaphore = asyncio.Semaphore(settings.max_concurrent_image_jobs)
    poll_interval = settings.image_worker_poll_interval

    async def process_with_semaphore(job: dict[str, Any]) -> None:
        async with semaphore:
            try:
                await _process_job(db, job)
            except Exception as e:
                logger.error("Job %s failed: %s", job["job_id"], e)
                await fail_job(db, job["job_id"], str(e))

    while True:
        try:
            job = await claim_next_job(db)
            if job is None:
                await asyncio.sleep(poll_interval)
                continue

            # Fire and forget with semaphore control
            asyncio.create_task(process_with_semaphore(job))

        except asyncio.CancelledError:
            logger.info("Image worker shutting down")
            break
        except Exception as e:
            logger.error("Image worker error: %s", e)
            await asyncio.sleep(poll_interval)


def start_image_worker(db: AsyncIOMotorDatabase) -> asyncio.Task:
    """Start the background image worker. Call during service lifespan startup."""
    global _worker_task
    _worker_task = asyncio.create_task(_worker_loop(db))
    logger.info(
        "Image worker started (max_concurrent=%d, poll_interval=%.1fs)",
        settings.max_concurrent_image_jobs,
        settings.image_worker_poll_interval,
    )
    return _worker_task


def stop_image_worker() -> None:
    """Stop the background image worker. Call during service lifespan shutdown."""
    global _worker_task
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()
        logger.info("Image worker stop requested")
    _worker_task = None
