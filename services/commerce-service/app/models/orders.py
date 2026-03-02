import secrets
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.profile import Address


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def generate_order_id() -> str:
    """Generate a unique order ID in ORD-YYYYMMDDHHMMSS-XXXXXX format."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    suffix = secrets.token_hex(3).upper()
    return f"ORD-{ts}-{suffix}"


ORDER_STATUSES = {"pending", "confirmed", "processing", "completed", "failed", "refunded"}


class OrderItem(BaseModel):
    item_id: str
    item_type: str
    name: str
    quantity: int
    unit_price: float
    total_price: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class Order(BaseModel):
    order_id: str = Field(default_factory=generate_order_id)
    user_id: str
    stripe_payment_intent_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    order_type: str = "one_time"  # "one_time" | "subscription"
    status: str = "pending"
    items: list[OrderItem] = Field(default_factory=list)
    subtotal: float = 0.0
    tax: float = 0.0
    shipping: float = 0.0
    total: float = 0.0
    shipping_address: Optional[Address] = None
    payment_method_summary: Optional[str] = None  # "Visa ****4242"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


SUBSCRIPTION_TIERS = {"premium", "ultra"}
SUBSCRIPTION_STATUSES = {"active", "past_due", "cancelled", "expired"}


class SubscriptionRecord(BaseModel):
    user_id: str
    stripe_subscription_id: str
    stripe_customer_id: str
    tier: str  # "premium" | "ultra"
    status: str = "active"
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class SubscriptionCreate(BaseModel):
    """Request body for creating a subscription."""

    tier: str


class TierChange(BaseModel):
    """Request body for changing subscription tier."""

    new_tier: str
