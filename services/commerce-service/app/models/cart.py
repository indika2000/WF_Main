from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CartItem(BaseModel):
    item_id: str
    item_type: str  # "subscription" | "one_time" | "pack" etc.
    name: str
    description: Optional[str] = None
    quantity: int = 1
    unit_price: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class Cart(BaseModel):
    user_id: str
    items: list[CartItem] = Field(default_factory=list)
    subtotal: float = 0.0
    tax: float = 0.0
    shipping: float = 0.0
    total: float = 0.0
    updated_at: datetime = Field(default_factory=_utcnow)


class CartItemAdd(BaseModel):
    """Request body for adding an item to cart."""

    item_id: str
    item_type: str
    name: str
    description: Optional[str] = None
    quantity: int = 1
    unit_price: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class CartItemUpdate(BaseModel):
    """Request body for updating an item quantity."""

    quantity: int
