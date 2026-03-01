from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class ImageVariant(BaseModel):
    width: int
    height: int
    storage_path: str
    file_size: int = 0


class ImageRecord(BaseModel):
    id: str
    user_id: str
    category: str = "general"
    filename: str
    content_type: str
    file_size: int
    width: int = 0
    height: int = 0
    storage_path: str
    variants: dict[str, ImageVariant] = Field(default_factory=dict)
    source: str = "upload"  # "upload" | "ai_generated"
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ImageUploadMeta(BaseModel):
    category: str = "general"
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class ImageUpdate(BaseModel):
    category: str | None = None
    metadata: dict[str, Any] | None = None
    tags: list[str] | None = None


class GenerateRequest(BaseModel):
    prompt: str
    category: str = "ai_generated"
    provider: str | None = None
    size: str = "1024x1024"
    quality: str = "standard"
    n: int = 1
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# Processing presets: each category defines variant sizes
PROCESSING_PRESETS: dict[str, dict[str, tuple[int, int]]] = {
    "profile": {
        "thumb": (64, 64),
        "medium": (256, 256),
        "large": (512, 512),
    },
    "card": {
        "thumb": (100, 140),
        "medium": (250, 350),
        "large": (500, 700),
    },
    "general": {
        "thumb": (150, 150),
        "medium": (400, 400),
        "large": (800, 800),
    },
}
