"""HTTP client for checking and recording character creation usage via the permissions service."""

import logging
import os
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

FEATURE_KEY = "character_creation"


def _get_headers() -> dict[str, str]:
    """Build auth headers for service-to-service calls."""
    api_key = os.environ.get("INTERNAL_API_KEY", "")
    return {"X-Api-Key": api_key}


async def check_character_usage(user_id: str) -> dict[str, Any]:
    """Check if a user can create another character.

    Returns: {allowed, used, limit, remaining, bonus, reason?}
    """
    url = f"{settings.permissions_service_url}/usage/{user_id}/{FEATURE_KEY}/check"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, headers=_get_headers())

        if response.status_code != 200:
            logger.error("Usage check failed: %s %s", response.status_code, response.text)
            return {"allowed": False, "reason": "service_error"}

        data = response.json()
        if data.get("success"):
            return data["data"]
        return {"allowed": False, "reason": "service_error"}

    except httpx.HTTPError as e:
        logger.error("Usage check HTTP error: %s", e)
        return {"allowed": False, "reason": "service_unavailable"}


async def record_character_usage(user_id: str) -> dict[str, Any] | None:
    """Record one character creation use.

    Returns: {used, limit, remaining, bonus} or None on failure.
    """
    url = f"{settings.permissions_service_url}/usage/{user_id}/{FEATURE_KEY}/record"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, headers=_get_headers())

        if response.status_code != 200:
            logger.error("Usage record failed: %s %s", response.status_code, response.text)
            return None

        data = response.json()
        if data.get("success"):
            return data["data"]
        return None

    except httpx.HTTPError as e:
        logger.error("Usage record HTTP error: %s", e)
        return None
