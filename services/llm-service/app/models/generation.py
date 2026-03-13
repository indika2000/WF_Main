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
    # Advanced options (Gemini Imagen)
    aspect_ratio: str | None = None
    negative_prompt: str | None = None
    safety_filter_level: str | None = None
    person_generation: str | None = None
    # Reference images (base64-encoded strings)
    style_reference_images: list[str] | None = None
    style_description: str | None = None
    subject_reference_images: list[str] | None = None


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
