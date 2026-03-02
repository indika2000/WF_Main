import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.models.profile import AddressCreate, AddressUpdate
from shared.python.auth import get_current_user
from shared.python.responses import error_response, success_response

router = APIRouter(prefix="/profile")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/{user_id}")
async def get_profile(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Get user's commerce profile."""
    profile = await db.commerce_profiles.find_one(
        {"user_id": user_id}, {"_id": 0}
    )
    if profile is None:
        # Return empty profile (auto-created on first purchase)
        return success_response(
            data={
                "user_id": user_id,
                "stripe_customer_id": None,
                "addresses": [],
            }
        )
    return success_response(data=profile)


@router.post("/{user_id}/addresses")
async def add_address(
    user_id: str,
    body: AddressCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Add a shipping address."""
    address = {"id": str(uuid.uuid4()), **body.model_dump()}

    # If this is the default, unset other defaults
    if address.get("is_default"):
        await db.commerce_profiles.update_one(
            {"user_id": user_id},
            {"$set": {"addresses.$[].is_default": False}},
        )

    await db.commerce_profiles.update_one(
        {"user_id": user_id},
        {
            "$push": {"addresses": address},
            "$set": {"updated_at": _utcnow()},
            "$setOnInsert": {
                "created_at": _utcnow(),
                "stripe_customer_id": None,
                "default_payment_method_id": None,
            },
        },
        upsert=True,
    )

    return success_response(data=address, message="Address added", status_code=201)


@router.patch("/{user_id}/addresses/{address_id}")
async def update_address(
    user_id: str,
    address_id: str,
    body: AddressUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Update a shipping address."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        return error_response(
            message="No fields to update",
            error_code="NO_UPDATES",
            status_code=400,
        )

    # If setting as default, unset other defaults first
    if updates.get("is_default"):
        await db.commerce_profiles.update_one(
            {"user_id": user_id},
            {"$set": {"addresses.$[].is_default": False}},
        )

    set_fields = {f"addresses.$.{k}": v for k, v in updates.items()}
    set_fields["updated_at"] = _utcnow()

    result = await db.commerce_profiles.update_one(
        {"user_id": user_id, "addresses.id": address_id},
        {"$set": set_fields},
    )

    if result.matched_count == 0:
        return error_response(
            message="Address not found",
            error_code="NOT_FOUND",
            status_code=404,
        )

    return success_response(message="Address updated")


@router.delete("/{user_id}/addresses/{address_id}")
async def delete_address(
    user_id: str,
    address_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Delete a shipping address."""
    result = await db.commerce_profiles.update_one(
        {"user_id": user_id},
        {
            "$pull": {"addresses": {"id": address_id}},
            "$set": {"updated_at": _utcnow()},
        },
    )

    if result.modified_count == 0:
        return error_response(
            message="Address not found",
            error_code="NOT_FOUND",
            status_code=404,
        )

    return success_response(message="Address deleted")
