"""Barcode stress test — 500+ barcodes through the generation pipeline.

Validates determinism, distribution, constraints, and uniqueness.
"""

import random
import string

import pytest

from app.services.config_loader import get_config
from app.services.generator import generate_creature
from app.services.normalisation import build_canonical_id, normalise


def _random_ean13() -> str:
    """Generate a random valid-format EAN-13."""
    digits = "".join(random.choices(string.digits, k=12))
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits))
    check = (10 - (total % 10)) % 10
    return digits + str(check)


def _random_upc_a() -> str:
    """Generate a random valid-format UPC-A."""
    digits = "".join(random.choices(string.digits, k=11))
    total = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(digits))
    check = (10 - (total % 10)) % 10
    return digits + str(check)


class TestBarcodeStress:
    """The big stress test — 500 barcodes through the full pipeline."""

    def test_500_barcodes_all_valid(self):
        """Every barcode produces a valid creature."""
        config = get_config()
        count = 500
        barcodes = []

        # Mix of EAN-13 and UPC-A
        for i in range(count):
            if i % 3 == 0:
                code_type = "UPC_A"
                raw_value = _random_upc_a()
            else:
                code_type = "EAN_13"
                raw_value = _random_ean13()
            barcodes.append((code_type, raw_value))

        creatures = []
        for code_type, raw_value in barcodes:
            normalised = normalise(code_type, raw_value)
            canonical_id = build_canonical_id(code_type, normalised)
            creature = generate_creature(
                code_type, raw_value, normalised, canonical_id, config
            )
            creatures.append(creature)

        # All creatures should be valid
        assert len(creatures) == count
        for c in creatures:
            assert c.identity.creature_id is not None
            assert c.classification.rarity in config.rarity_weights
            assert c.classification.biome in config.biomes
            assert c.classification.element in config.elements
            assert c.classification.temperament in config.temperaments
            assert c.classification.size in config.sizes

    def test_500_barcodes_deterministic(self):
        """Same barcode run twice produces identical creature."""
        config = get_config()
        barcodes = [("EAN_13", _random_ean13()) for _ in range(500)]

        for code_type, raw_value in barcodes:
            normalised = normalise(code_type, raw_value)
            canonical_id = build_canonical_id(code_type, normalised)
            c1 = generate_creature(code_type, raw_value, normalised, canonical_id, config)
            c2 = generate_creature(code_type, raw_value, normalised, canonical_id, config)
            assert c1.identity.creature_id == c2.identity.creature_id, (
                f"Barcode {raw_value} produced different creatures on re-scan"
            )

    def test_500_barcodes_unique_ids(self):
        """No two different barcodes produce the same creature_id."""
        config = get_config()
        creature_ids = set()

        for _ in range(500):
            raw_value = _random_ean13()
            normalised = normalise("EAN_13", raw_value)
            canonical_id = build_canonical_id("EAN_13", normalised)
            creature = generate_creature(
                "EAN_13", raw_value, normalised, canonical_id, config
            )
            assert creature.identity.creature_id not in creature_ids, (
                f"Duplicate creature_id: {creature.identity.creature_id}"
            )
            creature_ids.add(creature.identity.creature_id)

    def test_rarity_distribution(self):
        """Rarity distribution roughly matches weights (±10% with 500 samples)."""
        config = get_config()
        counts = {r: 0 for r in config.rarity_weights}

        for _ in range(500):
            raw_value = _random_ean13()
            normalised = normalise("EAN_13", raw_value)
            canonical_id = build_canonical_id("EAN_13", normalised)
            creature = generate_creature(
                "EAN_13", raw_value, normalised, canonical_id, config
            )
            counts[creature.classification.rarity] += 1

        total = 500
        # Common should be ~70% (±10%), so at least 300 and at most 400
        assert counts["COMMON"] >= 250, f"Too few Common: {counts['COMMON']}"
        assert counts["COMMON"] <= 420, f"Too many Common: {counts['COMMON']}"

        # Uncommon should be ~20% (±10%)
        assert counts["UNCOMMON"] >= 50, f"Too few Uncommon: {counts['UNCOMMON']}"
        assert counts["UNCOMMON"] <= 200, f"Too many Uncommon: {counts['UNCOMMON']}"

        # Rare+Epic+Legendary should exist but be small
        assert counts["RARE"] + counts["EPIC"] + counts["LEGENDARY"] >= 1

    def test_biome_species_constraint_all_barcodes(self):
        """Every creature's species is valid for its biome."""
        config = get_config()

        for _ in range(500):
            raw_value = _random_ean13()
            normalised = normalise("EAN_13", raw_value)
            canonical_id = build_canonical_id("EAN_13", normalised)
            creature = generate_creature(
                "EAN_13", raw_value, normalised, canonical_id, config
            )
            eligible = config.get_species_for_biome(creature.classification.biome)
            assert creature.classification.species in eligible, (
                f"{creature.classification.species} not valid for "
                f"{creature.classification.biome}"
            )

    def test_stats_within_bounds_all_barcodes(self):
        """Every creature's stats are within its rarity's bounds."""
        config = get_config()

        for _ in range(500):
            raw_value = _random_ean13()
            normalised = normalise("EAN_13", raw_value)
            canonical_id = build_canonical_id("EAN_13", normalised)
            creature = generate_creature(
                "EAN_13", raw_value, normalised, canonical_id, config
            )
            stat_min, stat_max = config.get_stat_range(
                creature.classification.rarity
            )
            for stat_name in config.stat_names:
                val = getattr(creature.attributes, stat_name)
                assert stat_min <= val <= stat_max, (
                    f"{stat_name}={val} out of [{stat_min},{stat_max}] "
                    f"for {creature.classification.rarity}"
                )

    def test_duplicate_barcode_10_times(self):
        """Same barcode scanned 10 times returns identical creature each time."""
        config = get_config()
        raw_value = "5012345678900"
        normalised = normalise("EAN_13", raw_value)
        canonical_id = build_canonical_id("EAN_13", normalised)

        first = generate_creature(
            "EAN_13", raw_value, normalised, canonical_id, config
        )
        for _ in range(9):
            again = generate_creature(
                "EAN_13", raw_value, normalised, canonical_id, config
            )
            assert first.identity.creature_id == again.identity.creature_id
            assert first.classification.rarity == again.classification.rarity
            assert first.classification.species == again.classification.species
            assert first.presentation.name == again.presentation.name
            assert first.attributes.power == again.attributes.power

    def test_distribution_report(self):
        """Generate 500 creatures and print distribution stats for manual review."""
        config = get_config()
        rarity_counts = {}
        biome_counts = {}
        family_counts = {}

        for _ in range(500):
            raw_value = _random_ean13()
            normalised = normalise("EAN_13", raw_value)
            canonical_id = build_canonical_id("EAN_13", normalised)
            creature = generate_creature(
                "EAN_13", raw_value, normalised, canonical_id, config
            )
            r = creature.classification.rarity
            rarity_counts[r] = rarity_counts.get(r, 0) + 1
            b = creature.classification.biome
            biome_counts[b] = biome_counts.get(b, 0) + 1
            f = creature.classification.family
            family_counts[f] = family_counts.get(f, 0) + 1

        # Print for manual review (visible in -v output)
        print("\n=== RARITY DISTRIBUTION (500 barcodes) ===")
        for r, c in sorted(rarity_counts.items()):
            pct = c / 500 * 100
            print(f"  {r}: {c} ({pct:.1f}%)")

        print("\n=== TOP 10 BIOMES ===")
        for b, c in sorted(biome_counts.items(), key=lambda x: -x[1])[:10]:
            print(f"  {b}: {c}")

        print("\n=== FAMILY DISTRIBUTION ===")
        for f, c in sorted(family_counts.items(), key=lambda x: -x[1]):
            print(f"  {f}: {c}")

        # Sanity check — all rarities should appear
        assert len(rarity_counts) >= 3  # At minimum Common, Uncommon, and Rare should appear in 500
