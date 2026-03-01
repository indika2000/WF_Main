import logging
from typing import Any

from app.providers.factory import provider_factory

logger = logging.getLogger("llm")


def list_providers() -> list[dict[str, Any]]:
    """List all providers with their capabilities and status."""
    return provider_factory.list_providers()


async def check_provider_status(name: str) -> dict[str, Any]:
    """Check if a specific provider is available and responsive.

    Performs a lightweight generation call to verify connectivity.
    """
    if not provider_factory.is_provider_available(name):
        return {
            "name": name,
            "status": "unavailable",
            "message": "Provider not configured or API key missing",
        }

    # Try a minimal text generation to verify the provider works
    text_provider = provider_factory.get_text_provider(name)
    if text_provider:
        try:
            await text_provider.generate(
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5,
                temperature=0,
            )
            return {
                "name": name,
                "status": "healthy",
                "message": "Provider is responsive",
            }
        except Exception as e:
            logger.warning("Provider health check failed for %s: %s", name, e)
            return {
                "name": name,
                "status": "error",
                "message": str(e),
            }

    return {
        "name": name,
        "status": "available",
        "message": "Provider configured (image-only, no health check)",
    }
