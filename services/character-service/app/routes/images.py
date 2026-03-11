"""Image generation status and SSE stream endpoints."""

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from sse_starlette.sse import EventSourceResponse

from app.database import get_db
from app.services.image_jobs import get_creature_image_status
from app.services.image_worker import (
    subscribe_creature_images,
    unsubscribe_creature_images,
)
from shared.python.auth import get_current_user
from shared.python.responses import success_response

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/creatures/{creature_id}/images")
async def get_image_status(
    creature_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get current image generation status for a creature."""
    jobs = await get_creature_image_status(db, creature_id)
    return success_response(data={"creature_id": creature_id, "jobs": jobs})


@router.get("/creatures/{creature_id}/images/stream")
async def stream_image_status(
    creature_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """SSE stream for real-time image readiness events.

    Events:
    - status: Initial status of all image jobs
    - image_ready: An image has been generated (includes image_type and image_id)
    - complete: All images are done
    - error: Something went wrong
    """

    async def event_generator():
        queue = subscribe_creature_images(creature_id)
        try:
            # Send initial status
            jobs = await get_creature_image_status(db, creature_id)
            yield {
                "event": "status",
                "data": json.dumps({
                    "creature_id": creature_id,
                    "jobs": jobs,
                }),
            }

            # Check if already complete
            completed = [j for j in jobs if j["status"] == "completed"]
            if len(completed) == 3:
                yield {
                    "event": "complete",
                    "data": json.dumps({"creature_id": creature_id}),
                }
                return

            # Wait for image readiness events
            images_received = len(completed)
            timeout = 300  # 5 minute max connection

            while images_received < 3:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=timeout)
                    yield {
                        "event": event.get("event", "image_ready"),
                        "data": json.dumps(event),
                    }
                    images_received += 1

                    if images_received >= 3:
                        yield {
                            "event": "complete",
                            "data": json.dumps({"creature_id": creature_id}),
                        }
                        break
                except asyncio.TimeoutError:
                    yield {
                        "event": "timeout",
                        "data": json.dumps({
                            "creature_id": creature_id,
                            "message": "Connection timed out",
                        }),
                    }
                    break

        except asyncio.CancelledError:
            pass
        finally:
            unsubscribe_creature_images(creature_id, queue)

    return EventSourceResponse(event_generator())
