import json
import logging
from datetime import datetime, timezone

from redis.asyncio import Redis

from app.config import settings
from app.models.cart import Cart, CartItem, CartItemAdd

logger = logging.getLogger("commerce")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _recalculate_totals(cart: Cart) -> None:
    """Recalculate cart totals from items. Server-side — never trust client."""
    cart.subtotal = sum(item.unit_price * item.quantity for item in cart.items)
    cart.tax = 0.0  # Digital goods — no tax for now
    cart.shipping = 0.0  # Digital delivery
    cart.total = cart.subtotal + cart.tax + cart.shipping
    cart.updated_at = _utcnow()


async def _save_cart(cart: Cart, r: Redis) -> None:
    """Save cart to Redis with TTL."""
    await r.set(
        f"cart:{cart.user_id}",
        cart.model_dump_json(),
        ex=settings.cart_ttl_seconds,
    )


async def get_cart(user_id: str, r: Redis) -> Cart | None:
    """Get the user's cart from Redis."""
    data = await r.get(f"cart:{user_id}")
    if not data:
        return None
    return Cart(**json.loads(data))


async def add_item(user_id: str, item_data: CartItemAdd, r: Redis) -> Cart:
    """Add an item to the cart. Merges quantity if item already exists."""
    cart = await get_cart(user_id, r)
    if cart is None:
        cart = Cart(user_id=user_id)

    # Check if item already exists — merge quantity
    for existing in cart.items:
        if existing.item_id == item_data.item_id:
            existing.quantity += item_data.quantity
            _recalculate_totals(cart)
            await _save_cart(cart, r)
            return cart

    # New item
    cart.items.append(CartItem(**item_data.model_dump()))
    _recalculate_totals(cart)
    await _save_cart(cart, r)
    return cart


async def update_item(
    user_id: str, item_id: str, quantity: int, r: Redis
) -> Cart | None:
    """Update item quantity. Removes item if quantity is 0."""
    cart = await get_cart(user_id, r)
    if cart is None:
        return None

    if quantity <= 0:
        cart.items = [i for i in cart.items if i.item_id != item_id]
    else:
        found = False
        for item in cart.items:
            if item.item_id == item_id:
                item.quantity = quantity
                found = True
                break
        if not found:
            return None

    _recalculate_totals(cart)
    await _save_cart(cart, r)
    return cart


async def remove_item(user_id: str, item_id: str, r: Redis) -> Cart | None:
    """Remove an item from the cart."""
    cart = await get_cart(user_id, r)
    if cart is None:
        return None

    original_len = len(cart.items)
    cart.items = [i for i in cart.items if i.item_id != item_id]
    if len(cart.items) == original_len:
        return None  # Item not found

    _recalculate_totals(cart)
    await _save_cart(cart, r)
    return cart


async def clear_cart(user_id: str, r: Redis) -> bool:
    """Clear the entire cart."""
    result = await r.delete(f"cart:{user_id}")
    return result > 0
