from datetime import datetime, timezone

from pydantic import BaseModel, Field


class UserCollectionEntry(BaseModel):
    """A user's ownership of a creature instance."""

    user_id: str
    creature_id: str
    obtained_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    obtained_via: str = "barcode_scan"  # "barcode_scan", "marketplace_purchase", "gift"
    source_canonical_id: str = ""
    is_tradeable: bool = True
    listed_for_sale: bool = False
