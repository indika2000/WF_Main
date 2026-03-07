"""Registry service — source tracking, collision detection, supply cap enforcement.

Handles all MongoDB operations for creature registration with atomic concurrency control.
"""

import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.models.creature import CreatureCard
from app.services.config_loader import get_config
from app.services.generator import generate_claimed_variant, generate_creature

logger = logging.getLogger(__name__)


async def check_existing_source(
    db: AsyncIOMotorDatabase, canonical_id: str
) -> dict | None:
    """Check if a barcode has already been registered."""
    return await db.source_registry.find_one({"canonical_id": canonical_id})


async def check_supply_cap(
    db: AsyncIOMotorDatabase, rarity: str, season: str
) -> bool:
    """Check if the supply cap for a rarity tier still has room.

    Returns True if there's room (or cap is unlimited), False if full.
    """
    config = get_config()
    max_count = config.supply_caps.get(rarity)
    if max_count is None:
        return True  # Unlimited

    counter = await db.supply_counters.find_one(
        {"counter_key": f"rarity:{rarity}", "season": season}
    )
    if counter is None:
        return True  # Counter not yet created, room available

    return counter["current_count"] < max_count


async def increment_supply_counter(
    db: AsyncIOMotorDatabase, rarity: str, season: str
) -> bool:
    """Atomically increment the supply counter for a rarity tier.

    Returns True if increment succeeded (room available), False if cap is full.
    Uses upsert to ensure counter exists, then atomic $inc with $lt guard.
    """
    config = get_config()
    max_count = config.supply_caps.get(rarity)
    if max_count is None:
        return True  # Unlimited, no counter needed

    # Ensure the counter document exists
    await db.supply_counters.update_one(
        {"counter_key": f"rarity:{rarity}", "season": season},
        {"$setOnInsert": {"current_count": 0, "max_count": max_count}},
        upsert=True,
    )

    # Atomically increment only if under the cap
    result = await db.supply_counters.update_one(
        {
            "counter_key": f"rarity:{rarity}",
            "season": season,
            "current_count": {"$lt": max_count},
        },
        {"$inc": {"current_count": 1}},
    )

    return result.modified_count > 0


async def check_collision(
    db: AsyncIOMotorDatabase, creature: CreatureCard
) -> bool:
    """Check if a creature's signature collides with an existing one.

    Returns True if there IS a collision (needs reroll), False if clear.
    """
    config = get_config()
    rarity = creature.classification.rarity
    policy = config.collision_policy.get(rarity, "ALLOW")

    if policy == "ALLOW":
        return False  # No collision checking for this rarity

    if policy == "ALLOW_IF_STATS_DIFFER":
        # Same signature from a different source is fine (stats will differ)
        return False

    if policy == "REROLL_ON_SIGNATURE_MATCH":
        # Exact signature match from a different source = collision
        existing = await db.creatures.find_one(
            {
                "identity.creature_signature": creature.identity.creature_signature,
                "source.canonical_id": {"$ne": creature.source.canonical_id},
            }
        )
        return existing is not None

    if policy == "REROLL_ON_ANY_ARCHETYPE_MATCH":
        # Even partial match (same species+biome at this rarity) = collision
        existing = await db.creatures.find_one(
            {
                "classification.rarity": rarity,
                "classification.biome": creature.classification.biome,
                "classification.species": creature.classification.species,
                "source.canonical_id": {"$ne": creature.source.canonical_id},
            }
        )
        return existing is not None

    return False


async def find_available_rarity(
    db: AsyncIOMotorDatabase, original_rarity: str, season: str
) -> str | None:
    """Find the next available rarity tier when the original is full.

    Walks down from the original rarity to COMMON.
    Returns None only if even COMMON is somehow full (shouldn't happen since it's unlimited).
    """
    config = get_config()
    rarities = config.get_rarities_ordered()

    # Find the index of the original rarity and walk down
    try:
        start_idx = rarities.index(original_rarity)
    except ValueError:
        return "COMMON"

    for rarity in rarities[start_idx + 1 :]:
        has_room = await check_supply_cap(db, rarity, season)
        if has_room:
            return rarity

    return None


async def register_creature(
    db: AsyncIOMotorDatabase,
    creature: CreatureCard,
    user_id: str,
) -> CreatureCard:
    """Register a creature in the database with full concurrency handling.

    This is the main entry point for persisting a new creature. It handles:
    1. Source registry (idempotency — same barcode returns same creature)
    2. Supply cap enforcement (atomic counter increment)
    3. Collision detection (with deterministic reroll)
    4. Creature persistence

    Returns the final registered creature (may differ from input if rerolled/downgraded).
    """
    config = get_config()
    season = config.version

    # Step 1: Try to register the source (unique index prevents duplicates)
    try:
        await db.source_registry.insert_one(
            {
                "canonical_id": creature.source.canonical_id,
                "creature_id": creature.identity.creature_id,
                "claimed_by": user_id,
            }
        )
    except DuplicateKeyError:
        # This barcode is already registered — return the existing creature
        existing_reg = await db.source_registry.find_one(
            {"canonical_id": creature.source.canonical_id}
        )
        if existing_reg:
            existing_creature = await db.creatures.find_one(
                {"identity.creature_id": existing_reg["creature_id"]}
            )
            if existing_creature:
                existing_creature.pop("_id", None)
                return CreatureCard(**existing_creature)
        # If somehow the registry entry exists but creature doesn't, continue
        # (shouldn't happen, but defensive)

    # Step 2: Check supply cap and handle downgrade if needed
    has_room = await increment_supply_counter(
        db, creature.classification.rarity, season
    )
    if not has_room:
        # Supply cap full — find next available rarity
        new_rarity = await find_available_rarity(
            db, creature.classification.rarity, season
        )
        if new_rarity:
            logger.info(
                "Supply cap full for %s, downgrading to %s for %s",
                creature.classification.rarity,
                new_rarity,
                creature.source.canonical_id,
            )
            # Re-generate with downgrade seed
            downgrade_canonical = (
                f"{creature.source.canonical_id}|downgrade|{new_rarity}"
            )
            from app.services.normalisation import build_canonical_id

            creature = generate_creature(
                code_type=creature.source.code_type,
                raw_value=creature.source.raw_value,
                normalised_value="",  # Not used in generation
                canonical_id=downgrade_canonical,
                config=config,
            )
            creature.downgraded_from = creature.classification.rarity
            # Override the rarity to the downgraded tier
            creature.classification.rarity = new_rarity

            # Try to increment the new rarity's counter
            await increment_supply_counter(db, new_rarity, season)
        else:
            logger.error("All supply caps full — this shouldn't happen")

    # Step 3: Check for collision (only for Epic/Legendary)
    collides = await check_collision(db, creature)
    if collides:
        # Deterministic reroll
        for iteration in range(1, config.max_reroll_attempts + 1):
            creature = generate_creature(
                code_type=creature.source.code_type,
                raw_value=creature.source.raw_value,
                normalised_value="",
                canonical_id=creature.source.canonical_id,
                config=config,
                reroll_iteration=iteration,
            )
            if not await check_collision(db, creature):
                logger.info(
                    "Collision resolved after %d reroll(s) for %s",
                    iteration,
                    creature.source.canonical_id,
                )
                break
        else:
            logger.warning(
                "Max reroll attempts reached for %s",
                creature.source.canonical_id,
            )

    # Step 4: Set ownership and persist
    creature.claimed_by = user_id
    creature.status = "claimed"

    try:
        await db.creatures.insert_one(creature.to_db_dict())
    except DuplicateKeyError:
        # Race condition — another request created this creature_id first
        existing = await db.creatures.find_one(
            {"identity.creature_id": creature.identity.creature_id}
        )
        if existing:
            existing.pop("_id", None)
            return CreatureCard(**existing)

    # Update the source registry with the final creature_id
    await db.source_registry.update_one(
        {"canonical_id": creature.source.canonical_id},
        {"$set": {"creature_id": creature.identity.creature_id}},
    )

    return creature


async def add_to_collection(
    db: AsyncIOMotorDatabase,
    user_id: str,
    creature_id: str,
    canonical_id: str,
    obtained_via: str = "barcode_scan",
) -> bool:
    """Add a creature to a user's collection. Returns True if added, False if already owned."""
    from datetime import datetime, timezone

    try:
        await db.user_collections.insert_one(
            {
                "user_id": user_id,
                "creature_id": creature_id,
                "obtained_at": datetime.now(timezone.utc),
                "obtained_via": obtained_via,
                "source_canonical_id": canonical_id,
                "is_tradeable": True,
                "listed_for_sale": False,
            }
        )
        return True
    except DuplicateKeyError:
        return False  # User already owns this creature


async def get_user_collection(
    db: AsyncIOMotorDatabase,
    user_id: str,
    skip: int = 0,
    limit: int = 50,
) -> list[dict]:
    """Get a user's creature collection with full creature details."""
    cursor = db.user_collections.find(
        {"user_id": user_id}
    ).skip(skip).limit(limit)
    entries = await cursor.to_list(length=limit)

    # Enrich each entry with the creature data
    for entry in entries:
        creature = await db.creatures.find_one(
            {"identity.creature_id": entry["creature_id"]}
        )
        if creature:
            creature.pop("_id", None)
        entry["creature"] = creature

    return entries


async def get_supply_status(
    db: AsyncIOMotorDatabase, season: str
) -> list[dict]:
    """Get current supply cap status for all rarity tiers."""
    config = get_config()
    result = []
    for rarity, max_count in config.supply_caps.items():
        counter = await db.supply_counters.find_one(
            {"counter_key": f"rarity:{rarity}", "season": season}
        )
        current = counter["current_count"] if counter else 0
        result.append(
            {
                "rarity": rarity,
                "current_count": current,
                "max_count": max_count,
                "remaining": (max_count - current) if max_count else None,
            }
        )
    return result
