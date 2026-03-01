import base64
import logging
from typing import Any, AsyncIterator

from google import genai
from google.genai import types

logger = logging.getLogger("llm")


class GeminiTextProvider:
    """Text generation using Google Gemini API."""

    name: str = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash", **kwargs):
        self.model = model
        self.client = genai.Client(api_key=api_key)
        self.timeout = kwargs.get("timeout", 30)

    async def generate(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        # Convert messages to Gemini format
        system_instruction = None
        contents = []
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            else:
                role = "model" if msg["role"] == "assistant" else "user"
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg["content"])],
                ))

        config = types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
            system_instruction=system_instruction,
        )

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )

        text = response.text or ""
        tokens = 0
        if response.usage_metadata:
            tokens = (
                (response.usage_metadata.prompt_token_count or 0)
                + (response.usage_metadata.candidates_token_count or 0)
            )

        return {
            "content": text,
            "tokens_used": tokens,
            "finish_reason": "stop",
        }

    async def stream(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        system_instruction = None
        contents = []
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            else:
                role = "model" if msg["role"] == "assistant" else "user"
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg["content"])],
                ))

        config = types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
            system_instruction=system_instruction,
        )

        async for chunk in self.client.aio.models.generate_content_stream(
            model=self.model,
            contents=contents,
            config=config,
        ):
            if chunk.text:
                yield chunk.text


class GeminiImageProvider:
    """Image generation using Google Imagen API."""

    name: str = "gemini"

    def __init__(self, api_key: str, model: str = "imagen-3.0-generate-002", **kwargs):
        self.model = model
        self.client = genai.Client(api_key=api_key)
        self.timeout = kwargs.get("timeout", 60)

    async def generate(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        n: int = 1,
    ) -> list[dict[str, Any]]:
        response = await self.client.aio.models.generate_images(
            model=self.model,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=n,
            ),
        )

        results = []
        for img in response.generated_images:
            results.append({
                "data": base64.b64encode(img.image.image_bytes).decode("utf-8"),
                "format": "png",
                "size": size,
            })
        return results
