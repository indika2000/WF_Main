import logging
from typing import Any, AsyncIterator

from app.providers.factory import provider_factory

logger = logging.getLogger("llm")


async def generate_text(
    prompt: str,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One-shot text generation with automatic fallback.

    Returns dict with content, provider, model, tokens_used, finish_reason.
    """
    config = config or {}
    provider = provider_factory.get_text_provider(config.get("provider"))
    if not provider:
        raise ValueError("No text provider available")

    messages = []
    if config.get("system_prompt"):
        messages.append({"role": "system", "content": config["system_prompt"]})
    messages.append({"role": "user", "content": prompt})

    try:
        result = await provider.generate(
            messages=messages,
            max_tokens=config.get("max_tokens", 4096),
            temperature=config.get("temperature", 0.7),
        )
        return {
            "content": result["content"],
            "provider": provider.name,
            "model": provider.model,
            "tokens_used": result["tokens_used"],
            "finish_reason": result["finish_reason"],
        }
    except Exception as e:
        logger.warning("Text generation failed with %s: %s", provider.name, e)

        # Try fallback
        fallback = provider_factory.get_fallback_text_provider(provider.name)
        if not fallback:
            raise

        logger.info("Falling back to %s for text generation", fallback.name)
        result = await fallback.generate(
            messages=messages,
            max_tokens=config.get("max_tokens", 4096),
            temperature=config.get("temperature", 0.7),
        )
        return {
            "content": result["content"],
            "provider": fallback.name,
            "model": fallback.model,
            "tokens_used": result["tokens_used"],
            "finish_reason": result["finish_reason"],
        }


async def stream_text(
    prompt: str,
    config: dict[str, Any] | None = None,
) -> AsyncIterator[str]:
    """Stream text generation. Yields SSE-formatted event strings.

    Events: start (provider info), chunk (content), end, error.
    """
    config = config or {}
    provider = provider_factory.get_text_provider(config.get("provider"))
    if not provider:
        yield f'{{"event": "error", "data": "No text provider available"}}'
        return

    messages = []
    if config.get("system_prompt"):
        messages.append({"role": "system", "content": config["system_prompt"]})
    messages.append({"role": "user", "content": prompt})

    import json

    yield json.dumps({
        "event": "start",
        "provider": provider.name,
        "model": provider.model,
    })

    try:
        async for chunk in provider.stream(
            messages=messages,
            max_tokens=config.get("max_tokens", 4096),
            temperature=config.get("temperature", 0.7),
        ):
            yield json.dumps({"event": "chunk", "data": chunk})

        yield json.dumps({"event": "end"})
    except Exception as e:
        logger.warning("Stream failed with %s: %s", provider.name, e)
        yield json.dumps({"event": "error", "data": str(e)})


async def generate_image(
    prompt: str,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Image generation with automatic fallback.

    Returns dict with images list, provider, model.
    """
    config = config or {}
    provider = provider_factory.get_image_provider(config.get("provider"))
    if not provider:
        raise ValueError("No image provider available")

    try:
        results = await provider.generate(
            prompt=prompt,
            size=config.get("size", "1024x1024"),
            quality=config.get("quality", "standard"),
            n=config.get("n", 1),
        )
        return {
            "images": results,
            "provider": provider.name,
            "model": provider.model,
        }
    except Exception as e:
        logger.warning("Image generation failed with %s: %s", provider.name, e)

        fallback = provider_factory.get_fallback_image_provider(provider.name)
        if not fallback:
            raise

        logger.info("Falling back to %s for image generation", fallback.name)
        results = await fallback.generate(
            prompt=prompt,
            size=config.get("size", "1024x1024"),
            quality=config.get("quality", "standard"),
            n=config.get("n", 1),
        )
        return {
            "images": results,
            "provider": fallback.name,
            "model": fallback.model,
        }
