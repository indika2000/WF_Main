from datetime import datetime, timezone

from pydantic import BaseModel, Field

SUBSCRIPTION_TIERS: dict = {
    "free": {
        "price": 0,
        "permissions": {
            "ad_free": False,
            "premium_features": False,
            "ai_text_generation": True,
            "ai_image_generation": False,
            "advanced_search": False,
            "unlimited_storage": False,
            "priority_support": False,
        },
        "feature_limits": {
            "ai_text_generation": 10,
            "ai_image_generation": 0,
        },
    },
    "premium": {
        "price": 4.99,
        "permissions": {
            "ad_free": True,
            "premium_features": True,
            "ai_text_generation": True,
            "ai_image_generation": True,
            "advanced_search": True,
            "unlimited_storage": False,
            "priority_support": False,
        },
        "feature_limits": {
            "ai_text_generation": 100,
            "ai_image_generation": 25,
        },
    },
    "ultra": {
        "price": 9.99,
        "permissions": {
            "ad_free": True,
            "premium_features": True,
            "ai_text_generation": True,
            "ai_image_generation": True,
            "advanced_search": True,
            "unlimited_storage": True,
            "priority_support": True,
        },
        "feature_limits": {
            "ai_text_generation": -1,  # Unlimited
            "ai_image_generation": -1,  # Unlimited
        },
    },
}


class Subscription(BaseModel):
    """User subscription record."""

    user_id: str
    tier: str = "free"  # free | premium | ultra
    status: str = "active"  # active | cancelled | expired | past_due
    stripe_subscription_id: str | None = None
    stripe_customer_id: str | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SubscriptionCreate(BaseModel):
    """Body for creating or updating a subscription."""

    tier: str = "free"
    status: str = "active"
    stripe_subscription_id: str | None = None
    stripe_customer_id: str | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
