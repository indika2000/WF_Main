from typing import Any

from fastapi import APIRouter, Depends
from redis.asyncio import Redis

from app.database import get_redis
from app.models.cart import CartItemAdd, CartItemUpdate
from app.services import cart_service
from shared.python.auth import get_current_user
from shared.python.responses import error_response, success_response

router = APIRouter(prefix="/cart")


@router.get("/{user_id}")
async def get_cart(
    user_id: str,
    r: Redis = Depends(get_redis),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Get the user's current cart."""
    cart = await cart_service.get_cart(user_id, r)
    if cart is None:
        return success_response(
            data={"user_id": user_id, "items": [], "total": 0.0}
        )
    return success_response(data=cart.model_dump(mode="json"))


@router.post("/{user_id}/items")
async def add_item(
    user_id: str,
    body: CartItemAdd,
    r: Redis = Depends(get_redis),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Add an item to the cart."""
    cart = await cart_service.add_item(user_id, body, r)
    return success_response(
        data=cart.model_dump(mode="json"), message="Item added to cart"
    )


@router.patch("/{user_id}/items/{item_id}")
async def update_item(
    user_id: str,
    item_id: str,
    body: CartItemUpdate,
    r: Redis = Depends(get_redis),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Update an item's quantity in the cart."""
    cart = await cart_service.update_item(user_id, item_id, body.quantity, r)
    if cart is None:
        return error_response(
            message="Cart or item not found",
            error_code="NOT_FOUND",
            status_code=404,
        )
    return success_response(
        data=cart.model_dump(mode="json"), message="Cart updated"
    )


@router.delete("/{user_id}/items/{item_id}")
async def remove_item(
    user_id: str,
    item_id: str,
    r: Redis = Depends(get_redis),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Remove an item from the cart."""
    cart = await cart_service.remove_item(user_id, item_id, r)
    if cart is None:
        return error_response(
            message="Cart or item not found",
            error_code="NOT_FOUND",
            status_code=404,
        )
    return success_response(
        data=cart.model_dump(mode="json"), message="Item removed"
    )


@router.delete("/{user_id}")
async def clear_cart(
    user_id: str,
    r: Redis = Depends(get_redis),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Clear the entire cart."""
    await cart_service.clear_cart(user_id, r)
    return success_response(message="Cart cleared")
