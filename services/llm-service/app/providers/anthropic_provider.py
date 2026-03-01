import logging
from typing import Any, AsyncIterator

import anthropic

logger = logging.getLogger("llm")


class AnthropicTextProvider:
    """Text generation using Anthropic's Claude API."""

    name: str = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514", **kwargs):
        self.model = model
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.timeout = kwargs.get("timeout", 30)

    async def generate(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        # Separate system message from conversation messages
        system_msg = None
        conv_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                conv_messages.append(msg)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": conv_messages,
        }
        if system_msg:
            kwargs["system"] = system_msg

        response = await self.client.messages.create(**kwargs)

        return {
            "content": response.content[0].text,
            "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
            "finish_reason": response.stop_reason or "stop",
        }

    async def stream(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        system_msg = None
        conv_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                conv_messages.append(msg)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": conv_messages,
        }
        if system_msg:
            kwargs["system"] = system_msg

        async with self.client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text
