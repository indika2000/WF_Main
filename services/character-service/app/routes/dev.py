"""Dev-only routes for testing character generation."""

import random
import string

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.services.config_loader import get_config
from app.services.generator import generate_creature
from app.services.normalisation import build_canonical_id, normalise
from shared.python.responses import success_response

router = APIRouter(prefix="/dev")


def _random_ean13() -> str:
    """Generate a random valid-format EAN-13 barcode."""
    digits = "".join(random.choices(string.digits, k=12))
    # Calculate check digit (simple mod-10 algorithm)
    total = 0
    for i, d in enumerate(digits):
        total += int(d) * (1 if i % 2 == 0 else 3)
    check = (10 - (total % 10)) % 10
    return digits + str(check)


@router.post("/generate-preview")
async def generate_preview(
    code_type: str = "EAN_13",
    raw_value: str | None = None,
):
    """Generate a creature preview WITHOUT persisting. For testing only.

    If no raw_value is provided, generates a random barcode.
    """
    config = get_config()

    if raw_value is None:
        raw_value = _random_ean13()
        code_type = "EAN_13"

    normalised = normalise(code_type, raw_value)
    canonical_id = build_canonical_id(code_type, normalised)

    creature = generate_creature(
        code_type=code_type,
        raw_value=raw_value,
        normalised_value=normalised,
        canonical_id=canonical_id,
        config=config,
    )

    return success_response(
        data={
            "creature": creature.to_db_dict(),
            "canonical_id": canonical_id,
            "barcode": raw_value,
        },
        message="Preview only — not persisted",
    )


@router.post("/batch-generate")
async def batch_generate(
    count: int = 100,
):
    """Generate a batch of random creatures and return distribution stats.

    Does NOT persist to database — purely for testing generation distribution.
    """
    config = get_config()
    rarity_counts: dict[str, int] = {}
    biome_counts: dict[str, int] = {}
    family_counts: dict[str, int] = {}
    creatures = []

    for _ in range(min(count, 500)):
        barcode = _random_ean13()
        normalised = normalise("EAN_13", barcode)
        canonical_id = build_canonical_id("EAN_13", normalised)

        creature = generate_creature(
            code_type="EAN_13",
            raw_value=barcode,
            normalised_value=normalised,
            canonical_id=canonical_id,
            config=config,
        )

        rarity = creature.classification.rarity
        rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1
        biome = creature.classification.biome
        biome_counts[biome] = biome_counts.get(biome, 0) + 1
        family = creature.classification.family
        family_counts[family] = family_counts.get(family, 0) + 1

        creatures.append(
            {
                "creature_id": creature.identity.creature_id,
                "name": creature.presentation.name,
                "rarity": rarity,
                "biome": biome,
                "species": creature.classification.species,
                "element": creature.classification.element,
            }
        )

    return success_response(
        data={
            "count": len(creatures),
            "distribution": {
                "rarity": rarity_counts,
                "biome": dict(sorted(biome_counts.items(), key=lambda x: -x[1])),
                "family": dict(sorted(family_counts.items(), key=lambda x: -x[1])),
            },
            "creatures": creatures,
        },
        message=f"Generated {len(creatures)} creatures (preview only)",
    )


@router.post("/reset-supply-counters")
async def reset_supply_counters(
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Reset all supply counters for testing. Dev only."""
    result = await db.supply_counters.delete_many({})
    return success_response(
        data={"deleted": result.deleted_count},
        message="Supply counters reset",
    )


@router.get("/config-stats")
async def config_stats():
    """Get stats about the loaded generation config."""
    config = get_config()

    total_subtypes = sum(
        sum(len(v) for v in species_map.values())
        for species_map in config.subtype_map.values()
    )

    return success_response(
        data={
            "version": config.version,
            "biomes": len(config.biomes),
            "species": len(config._species_ids),
            "subtypes_total": total_subtypes,
            "elements": len(config.elements),
            "temperaments": len(config.temperaments),
            "sizes": len(config.sizes),
            "variants": len(config.variants),
            "primary_colors": len(config.primary_colors),
            "secondary_colors": len(config.secondary_colors),
            "rarity_tiers": list(config.rarity_weights.keys()),
            "supply_caps": config.supply_caps,
        }
    )
