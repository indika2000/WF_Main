from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class Source(BaseModel):
    """Where this creature came from."""

    canonical_id: str  # "EAN_13|5012345678900|WILDERNESS_FRIENDS|v1"
    code_type: str  # "EAN_13", "UPC_A", "QR"
    raw_value: str  # Original scanned value


class Classification(BaseModel):
    """What this creature is — deterministic from the seed."""

    rarity: str  # COMMON, UNCOMMON, RARE, EPIC, LEGENDARY
    biome: str
    family: str
    species: str
    sub_type: str
    element: str
    temperament: str
    size: str
    variant: str


class Presentation(BaseModel):
    """How this creature is displayed."""

    name: str  # "Frostborn Ice Dragon"
    title: str  # "The Warden of Hollow Pines"
    primary_color: str
    secondary_color: str
    sigil: str
    frame_style: str


class Attributes(BaseModel):
    """Creature stats — rarity-biased from seed bytes."""

    power: int
    defense: int
    agility: int
    wisdom: int
    ferocity: int
    magic: int
    luck: int


class Identity(BaseModel):
    """Unique identification for this creature."""

    creature_id: str  # "WF-v1-RARE-FOREST-ELF-8A4C91B2"
    creature_signature: str  # "RARE|FOREST|ELF|GROVE_ELF|EARTH|MEDIUM|CAUTIOUS|MOSSBOUND"


class CreatureImages(BaseModel):
    """Image references for a creature — populated asynchronously by image worker."""

    card: Optional[str] = None  # Image service ID for card artwork
    headshot_color: Optional[str] = None  # Image service ID for color headshot
    headshot_pencil: Optional[str] = None  # Image service ID for pencil sketch
    artist_id: Optional[str] = None  # Artist persona used for generation


class CreatureCard(BaseModel):
    """The complete creature definition — global, one per creature_id."""

    identity: Identity
    source: Source
    classification: Classification
    presentation: Presentation
    attributes: Attributes
    season: str = "v1"
    images: CreatureImages = Field(default_factory=CreatureImages)
    claimed_by: Optional[str] = None
    claimed_at: Optional[datetime] = None
    status: str = "unclaimed"  # "unclaimed", "claimed", "released"
    generation_iteration: int = 0  # 0 = no reroll, 1+ = rerolled
    downgraded_from: Optional[str] = None  # original rarity if downgraded
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_db_dict(self) -> dict:
        """Convert to a flat dict for MongoDB insertion."""
        d = self.model_dump()
        return d


class CreatureResponse(BaseModel):
    """API response for a creature — includes ownership context."""

    creature: CreatureCard
    is_owner: bool = False
    is_new_discovery: bool = False
    is_claimed_variant: bool = False  # True if user got Common variant because someone else claimed first
