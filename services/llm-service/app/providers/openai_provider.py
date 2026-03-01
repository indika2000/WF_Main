import base64
import logging
from typing import Any, AsyncIterator

import openai

logger = logging.getLogger("llm")


class OpenAITextProvider:
    """Text generation using OpenAI's API."""

    name: str = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o", **kwargs):
        self.model = model
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.timeout = kwargs.get("timeout", 30)

    async def generate(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        choice = response.choices[0]
        return {
            "content": choice.message.content or "",
            "tokens_used": response.usage.total_tokens if response.usage else 0,
            "finish_reason": choice.finish_reason or "stop",
        }

    async def stream(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class OpenAIImageProvider:
    """Image generation using OpenAI's DALL-E API."""

    name: str = "openai"

    def __init__(self, api_key: str, model: str = "dall-e-3", **kwargs):
        self.model = model
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.timeout = kwargs.get("timeout", 60)

    async def generate(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        n: int = 1,
    ) -> list[dict[str, Any]]:
        response = await self.client.images.generate(
            model=self.model,
            prompt=prompt,
            size=size,
            quality=quality,
            n=n,
            response_format="b64_json",
        )

        results = []
        for img_data in response.data:
            results.append({
                "data": img_data.b64_json,
                "format": "png",
                "size": size,
            })
        return results
