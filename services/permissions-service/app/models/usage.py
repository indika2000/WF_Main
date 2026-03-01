from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field


def _default_period_end() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=30)


class FeatureUsage(BaseModel):
    """Tracks metered feature usage per user."""

    user_id: str
    feature: str  # e.g. "ai_text_generation"
    used: int = 0
    limit: int = 0  # Monthly limit (-1 = unlimited)
    bonus: int = 0  # Extra uses from promotions/ads
    period_start: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    period_end: datetime = Field(default_factory=_default_period_end)
    last_used_at: datetime | None = None


class UsageCheckResponse(BaseModel):
    """Response for a usage check."""

    user_id: str
    feature: str
    allowed: bool
    used: int
    limit: int
    bonus: int
    remaining: int
    reason: str | None = None


class BonusRequest(BaseModel):
    """Body for adding bonus uses."""

    amount: int
