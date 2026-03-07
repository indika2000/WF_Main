from datetime import datetime, timezone

from pydantic import BaseModel, Field


class SourceRegistryEntry(BaseModel):
    """Maps a canonical barcode ID to a creature ID. One-to-one."""

    canonical_id: str
    creature_id: str
    claimed_by: str  # user_id of first scanner
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SupplyCounter(BaseModel):
    """Tracks supply cap usage per rarity tier per season."""

    counter_key: str  # "rarity:LEGENDARY" or "archetype:LEGENDARY|*|DRAGON|*"
    season: str  # "v1"
    current_count: int = 0
    max_count: int | None = None  # None = unlimited


class GenerationRequest(BaseModel):
    """Incoming request to generate a creature from a barcode scan."""

    code_type: str  # "EAN_13", "UPC_A", "QR"
    raw_value: str

    class Config:
        json_schema_extra = {
            "example": {
                "code_type": "EAN_13",
                "raw_value": "5012345678900",
            }
        }
