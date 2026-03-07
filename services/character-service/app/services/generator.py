"""Deterministic creature generation from a barcode seed.

The core algorithm: canonical_id → SHA-256 → byte allocation → creature card.
Same input always produces the same output.
"""

import hashlib
from datetime import datetime, timezone
from typing import Any

from app.models.creature import (
    Attributes,
    Classification,
    CreatureCard,
    Identity,
    Presentation,
    Source,
)
from app.services.config_loader import GenerationConfig, get_config


def _hash_seed(canonical_id: str) -> bytes:
    """SHA-256 hash of the canonical ID, returning 32 bytes."""
    return hashlib.sha256(canonical_id.encode("utf-8")).digest()


def _pick(byte_val: int, options: list) -> Any:
    """Deterministically pick from a list using a byte value."""
    if not options:
        raise ValueError("Cannot pick from empty list")
    return options[byte_val % len(options)]


def generate_creature(
    code_type: str,
    raw_value: str,
    normalised_value: str,
    canonical_id: str,
    config: GenerationConfig | None = None,
    reroll_iteration: int = 0,
) -> CreatureCard:
    """Generate a creature card from a canonical barcode ID.

    This is a PURE function — no DB calls, no side effects.
    Same inputs always produce the same creature.

    Args:
        code_type: The barcode type (EAN_13, UPC_A, QR)
        raw_value: The original scanned value
        normalised_value: The normalised barcode value
        canonical_id: The full canonical identity string
        config: Generation config (uses global singleton if None)
        reroll_iteration: 0 = first attempt, 1+ = reroll for collision

    Returns:
        A complete CreatureCard (not yet persisted)
    """
    if config is None:
        config = get_config()

    # Derive seed — includes reroll iteration for collision handling
    if reroll_iteration == 0:
        seed_input = canonical_id
    else:
        seed_input = f"{canonical_id}|reroll|{reroll_iteration}"

    seed = _hash_seed(seed_input)

    # ── Byte allocation ────────────────────────────────────────
    # byte[0]   → rarity
    # byte[1]   → biome
    # byte[2]   → (reserved — family derived from species)
    # byte[3]   → species
    # byte[4]   → subtype
    # byte[5]   → element
    # byte[6]   → temperament
    # byte[7]   → size
    # byte[8]   → variant
    # byte[9]   → title role
    # byte[10]  → primary colour
    # byte[11]  → secondary colour
    # byte[12]  → sigil
    # byte[13]  → frame style
    # byte[14-20] → stats
    # byte[21+] → lore/domain, future expansion

    rarity = config.get_rarity(seed[0])
    biome = _pick(seed[1], config.biomes)

    # Species constrained by biome
    eligible_species = config.get_species_for_biome(biome)
    species = _pick(seed[3], eligible_species)
    family = config.get_family(species)

    # Subtype constrained by species + biome
    subtypes = config.get_subtypes(species, biome)
    sub_type = _pick(seed[4], subtypes)

    element = _pick(seed[5], config.elements)
    temperament = _pick(seed[6], config.temperaments)
    size = _pick(seed[7], config.sizes)
    variant = _pick(seed[8], config.variants)

    # Presentation
    role = _pick(seed[9], config.roles)
    primary_color = _pick(seed[10], config.primary_colors)
    secondary_color = _pick(seed[11], config.secondary_colors)
    sigil = _pick(seed[12], config.sigils)
    frame_style = _pick(seed[13], config.frame_styles)
    domain = _pick(seed[21], config.domains)

    # Stats — rarity-biased
    stat_min, stat_max = config.get_stat_range(rarity)
    stat_range_size = stat_max - stat_min + 1
    stats = {}
    for i, stat_name in enumerate(config.stat_names):
        byte_idx = 14 + i
        if byte_idx < len(seed):
            stats[stat_name] = stat_min + (seed[byte_idx] % stat_range_size)
        else:
            stats[stat_name] = stat_min

    # Name and title
    variant_display = variant.replace("_", " ").title()
    sub_type_display = sub_type.replace("_", " ").title()
    name = f"{variant_display} {sub_type_display}"
    title = f"The {role} of {domain}"

    # Creature signature (for collision detection)
    signature = f"{rarity}|{biome}|{species}|{sub_type}|{element}|{size}|{temperament}|{variant}"

    # Creature ID — includes version and a hash fragment for uniqueness
    hash_fragment = seed[:4].hex().upper()
    creature_id = f"WF-{config.version}-{rarity}-{biome}-{species}-{hash_fragment}"

    return CreatureCard(
        identity=Identity(
            creature_id=creature_id,
            creature_signature=signature,
        ),
        source=Source(
            canonical_id=canonical_id,
            code_type=code_type,
            raw_value=raw_value,
        ),
        classification=Classification(
            rarity=rarity,
            biome=biome,
            family=family,
            species=species,
            sub_type=sub_type,
            element=element,
            temperament=temperament,
            size=size,
            variant=variant,
        ),
        presentation=Presentation(
            name=name,
            title=title,
            primary_color=primary_color,
            secondary_color=secondary_color,
            sigil=sigil,
            frame_style=frame_style,
        ),
        attributes=Attributes(**stats),
        season=config.version,
        generation_iteration=reroll_iteration,
    )


def generate_claimed_variant(
    code_type: str,
    raw_value: str,
    normalised_value: str,
    canonical_id: str,
    config: GenerationConfig | None = None,
) -> CreatureCard:
    """Generate a Common variant for a barcode that's already been claimed.

    Uses a different seed derivation to produce a deterministic but
    different creature — always Common tier.
    """
    if config is None:
        config = get_config()

    claimed_canonical = f"{canonical_id}|claimed_variant"
    seed = _hash_seed(claimed_canonical)

    # Force Common rarity
    biome = _pick(seed[1], config.biomes)
    eligible_species = config.get_species_for_biome(biome)
    species = _pick(seed[3], eligible_species)
    family = config.get_family(species)
    subtypes = config.get_subtypes(species, biome)
    sub_type = _pick(seed[4], subtypes)

    element = _pick(seed[5], config.elements)
    temperament = _pick(seed[6], config.temperaments)
    size = _pick(seed[7], config.sizes)
    variant = _pick(seed[8], config.variants)

    role = _pick(seed[9], config.roles)
    primary_color = _pick(seed[10], config.primary_colors)
    secondary_color = _pick(seed[11], config.secondary_colors)
    sigil = _pick(seed[12], config.sigils)
    frame_style = _pick(seed[13], config.frame_styles)
    domain = _pick(seed[21], config.domains)

    stat_min, stat_max = config.get_stat_range("COMMON")
    stat_range_size = stat_max - stat_min + 1
    stats = {}
    for i, stat_name in enumerate(config.stat_names):
        byte_idx = 14 + i
        if byte_idx < len(seed):
            stats[stat_name] = stat_min + (seed[byte_idx] % stat_range_size)
        else:
            stats[stat_name] = stat_min

    variant_display = variant.replace("_", " ").title()
    sub_type_display = sub_type.replace("_", " ").title()
    name = f"{variant_display} {sub_type_display}"
    title = f"The {role} of {domain}"

    signature = f"COMMON|{biome}|{species}|{sub_type}|{element}|{size}|{temperament}|{variant}"
    hash_fragment = seed[:4].hex().upper()
    creature_id = f"WF-{config.version}-COMMON-{biome}-{species}-{hash_fragment}"

    return CreatureCard(
        identity=Identity(
            creature_id=creature_id,
            creature_signature=signature,
        ),
        source=Source(
            canonical_id=f"{canonical_id}|claimed_variant",
            code_type=code_type,
            raw_value=raw_value,
        ),
        classification=Classification(
            rarity="COMMON",
            biome=biome,
            family=family,
            species=species,
            sub_type=sub_type,
            element=element,
            temperament=temperament,
            size=size,
            variant=variant,
        ),
        presentation=Presentation(
            name=name,
            title=title,
            primary_color=primary_color,
            secondary_color=secondary_color,
            sigil=sigil,
            frame_style=frame_style,
        ),
        attributes=Attributes(**stats),
        season=config.version,
        generation_iteration=0,
    )
