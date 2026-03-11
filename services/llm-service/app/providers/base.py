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
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Generate images. Returns list of {data (base64), format, size}.

        Optional kwargs for advanced providers:
            aspect_ratio: str — e.g. "3:4", "1:1" (Gemini Imagen)
            negative_prompt: str — elements to exclude (Gemini Imagen)
            style_reference_images: list[bytes] — style ref images (Gemini Imagen)
            style_description: str — style description for refs (Gemini Imagen)
            subject_reference_images: list[bytes] — subject ref images (Gemini Imagen)
        """
        ...
