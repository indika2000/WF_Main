"""POST /generate — main endpoint for scanning a barcode and generating a creature."""

import logging

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.models.registry import GenerationRequest
from app.services.config_loader import get_config
from app.services.generator import generate_creature, generate_claimed_variant
from app.services.normalisation import NormalisationError, normalise, build_canonical_id
from app.services.registry import (
    add_to_collection,
    check_existing_source,
    register_creature,
)
from shared.python.auth import get_current_user
from shared.python.responses import error_response, success_response

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/generate")
async def generate(
    body: GenerationRequest,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Scan a barcode and generate (or retrieve) a creature.

    Flow:
    1. Normalise the barcode
    2. Check if this barcode was already scanned
       - If by this user: return existing creature
       - If by another user: generate claimed variant (Common)
       - If new: generate and register the creature
    3. Add creature to user's collection
    """
    user_id = user["uid"]

    # Step 1: Normalise
    try:
        normalised = normalise(body.code_type, body.raw_value)
    except NormalisationError as e:
        return error_response(
            message=str(e),
            error_code="INVALID_BARCODE",
            status_code=400,
        )

    canonical_id = build_canonical_id(body.code_type, normalised)

    # Step 2: Check existing
    existing = await check_existing_source(db, canonical_id)

    if existing:
        # Barcode already registered
        existing_creature_doc = await db.creatures.find_one(
            {"identity.creature_id": existing["creature_id"]}
        )

        if existing and existing.get("claimed_by") == user_id:
            # Same user scanning again — return their creature
            added = await add_to_collection(
                db, user_id, existing["creature_id"], canonical_id
            )
            if existing_creature_doc:
                existing_creature_doc.pop("_id", None)
            return success_response(
                data={
                    "creature": existing_creature_doc,
                    "is_owner": True,
                    "is_new_discovery": False,
                    "is_claimed_variant": False,
                },
                message="Creature already in your collection",
            )
        else:
            # Different user — they get a Common variant
            config = get_config()
            variant_creature = generate_claimed_variant(
                code_type=body.code_type,
                raw_value=body.raw_value,
                normalised_value=normalised,
                canonical_id=canonical_id,
                config=config,
            )

            # Register the variant (using its own canonical_id which includes |claimed_variant)
            variant_creature = await register_creature(
                db, variant_creature, user_id
            )
            await add_to_collection(
                db,
                user_id,
                variant_creature.identity.creature_id,
                variant_creature.source.canonical_id,
            )

            return success_response(
                data={
                    "creature": variant_creature.to_db_dict(),
                    "is_owner": True,
                    "is_new_discovery": True,
                    "is_claimed_variant": True,
                },
                message="This barcode was already claimed — you received a Common variant",
            )

    # Step 3: New barcode — generate and register
    config = get_config()
    creature = generate_creature(
        code_type=body.code_type,
        raw_value=body.raw_value,
        normalised_value=normalised,
        canonical_id=canonical_id,
        config=config,
    )

    creature = await register_creature(db, creature, user_id)

    await add_to_collection(
        db, user_id, creature.identity.creature_id, canonical_id
    )

    logger.info(
        "New creature generated: %s (%s) for user %s",
        creature.identity.creature_id,
        creature.classification.rarity,
        user_id,
    )

    return success_response(
        data={
            "creature": creature.to_db_dict(),
            "is_owner": True,
            "is_new_discovery": True,
            "is_claimed_variant": False,
        },
        message=f"New {creature.classification.rarity} creature discovered!",
    )
