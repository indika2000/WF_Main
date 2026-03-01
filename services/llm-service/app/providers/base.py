from typing import Any, AsyncIterator, Protocol, runtime_checkable


@runtime_checkable
class TextProvider(Protocol):
    """Protocol for text generation providers."""

    name: str
    model: str

    async def generate(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """Generate a text response. Returns {content, tokens_used, finish_reason}."""
        ...

    async def stream(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream text chunks. Yields partial content strings."""
        ...


@runtime_checkable
class ImageProvider(Protocol):
    """Protocol for image generation providers."""

    name: str
    model: str

    async def generate(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        n: int = 1,
    ) -> list[dict[str, Any]]:
        """Generate images. Returns list of {data (base64), format, size}."""
        ...
