from typing import Any

from pydantic import BaseModel, Field


class TextGenConfig(BaseModel):
    provider: str | None = None
    model: str | None = None
    max_tokens: int = 4096
    temperature: float = 0.7
    system_prompt: str | None = None


class TextGenRequest(BaseModel):
    prompt: str
    config: TextGenConfig = Field(default_factory=TextGenConfig)


class TextResult(BaseModel):
    content: str
    provider: str
    model: str
    tokens_used: int
    finish_reason: str


class ImageGenConfig(BaseModel):
    provider: str | None = None
    size: str = "1024x1024"
    quality: str = "standard"
    style: str | None = None
    n: int = 1


class ImageGenRequest(BaseModel):
    prompt: str
    config: ImageGenConfig = Field(default_factory=ImageGenConfig)


class GeneratedImage(BaseModel):
    data: str | None = None  # base64 encoded
    url: str | None = None
    format: str = "png"
    size: str = "1024x1024"


class ImageResult(BaseModel):
    images: list[GeneratedImage]
    provider: str
    model: str
