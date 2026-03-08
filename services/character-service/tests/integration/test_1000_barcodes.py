"""Comprehensive 1000-barcode test suite.

Tests determinism, uniqueness, season isolation, biome weight distribution,
rarity distribution, biome-species constraints, stat ranges, and claimed variants.
"""

import random
import string
from collections import Counter

import pytest

from app.services.config_loader import get_config
from app.services.generator import generate_creature, generate_claimed_variant
from app.services.normalisation import build_canonical_id, normalise


# ── Barcode Corpus (deterministic, shared across all tests) ──────────────────

_rng = random.Random(42)


def _random_ean13(rng: random.Random) -> str:
    digits = "".join(rng.choices(string.digits, k=12))
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits))
    check = (10 - (total % 10)) % 10
    return digits + str(check)


def _random_upc_a(rng: random.Random) -> str:
    digits = "".join(rng.choices(string.digits, k=11))
    total = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(digits))
    check = (10 - (total % 10)) % 10
    return digits + str(check)


# 1000 barcodes: ~333 UPC-A, ~667 EAN-13
BARCODE_CORPUS: list[tuple[str, str]] = []
for _i in range(1000):
    if _i % 3 == 0:
        BARCODE_CORPUS.append(("UPC_A", _random_upc_a(_rng)))
    else:
        BARCODE_CORPUS.append(("EAN_13", _random_ean13(_rng)))

AQUATIC_BIOMES = frozenset({
    "SWAMP", "MANGROVE_SWAMP", "BOG",
    "OCEAN", "DEEP_OCEAN", "CORAL_REEF",
    "RIVER", "LAKE", "WATERFALL",
    "ISLAND", "COAST",
})


# ── Helper ───────────────────────────────────────────────────────────────────

def _generate_all(config, version_override=None):
    """Generate creatures for the full corpus with the given config."""
    creatures = []
    for code_type, raw_value in BARCODE_CORPUS:
        normalised = normalise(code_type, raw_value)
        if version_override:
            canonical_id = f"{code_type}|{normalised}|WILDERNESS_FRIENDS|{version_override}"
        else:
            canonical_id = build_canonical_id(code_type, normalised)
        creature = generate_creature(
            code_type, raw_value, normalised, canonical_id, config
        )
        creatures.append(creature)
    return creatures


# ── a) Determinism ───────────────────────────────────────────────────────────


class TestDeterminism1000:
    """Same barcode -> identical creature, run twice."""

    def test_1000_barcodes_deterministic(self):
        config = get_config()
        for code_type, raw_value in BARCODE_CORPUS:
            normalised = normalise(code_type, raw_value)
            canonical_id = build_canonical_id(code_type, normalised)
            c1 = generate_creature(code_type, raw_value, normalised, canonical_id, config)
            c2 = generate_creature(code_type, raw_value, normalised, canonical_id, config)
            assert c1.identity.creature_id == c2.identity.creature_id
            assert c1.classification.rarity == c2.classification.rarity
            assert c1.classification.biome == c2.classification.biome
            assert c1.classification.species == c2.classification.species
            assert c1.attributes.power == c2.attributes.power


# ── b) Cross-Barcode Uniqueness ──────────────────────────────────────────────


class TestCrossBarcodeUniqueness:
    """1000 different barcodes -> high % of unique creature_ids."""

    def test_unique_creature_ids(self):
        config = get_config()
        creatures = _generate_all(config)
        creature_ids = {c.identity.creature_id for c in creatures}
        assert len(creature_ids) >= 990, (
            f"Only {len(creature_ids)}/1000 unique creature_ids"
        )


# ── c) Season Isolation ──────────────────────────────────────────────────────


class TestSeasonIsolation:
    """Same barcodes with v1 vs v2 config -> completely different creatures."""

    def test_v1_v2_different_creatures(self, v2_config):
        v1_config = get_config()
        subset = BARCODE_CORPUS[:100]

        for code_type, raw_value in subset:
            normalised = normalise(code_type, raw_value)
            v1_canonical = f"{code_type}|{normalised}|WILDERNESS_FRIENDS|v1"
            v2_canonical = f"{code_type}|{normalised}|WILDERNESS_FRIENDS|v2"

            c_v1 = generate_creature(code_type, raw_value, normalised, v1_canonical, v1_config)
            c_v2 = generate_creature(code_type, raw_value, normalised, v2_canonical, v2_config)

            assert c_v1.identity.creature_id != c_v2.identity.creature_id, (
                f"Barcode {raw_value} produced same creature across seasons"
            )

    def test_v1_v2_zero_overlap_in_ids(self, v2_config):
        v1_config = get_config()
        subset = BARCODE_CORPUS[:100]

        v1_ids = set()
        v2_ids = set()
        for code_type, raw_value in subset:
            normalised = normalise(code_type, raw_value)
            v1_canonical = f"{code_type}|{normalised}|WILDERNESS_FRIENDS|v1"
            v2_canonical = f"{code_type}|{normalised}|WILDERNESS_FRIENDS|v2"
            v1_ids.add(
                generate_creature(code_type, raw_value, normalised, v1_canonical, v1_config)
                .identity.creature_id
            )
            v2_ids.add(
                generate_creature(code_type, raw_value, normalised, v2_canonical, v2_config)
                .identity.creature_id
            )
        assert v1_ids.isdisjoint(v2_ids), "Season v1 and v2 share creature IDs"


# ── d) Biome Weight Distribution ─────────────────────────────────────────────


class TestBiomeWeightDistribution:
    """Verify weighted biome selection produces expected distribution."""

    def test_aquatic_biome_proportion(self, v2_config):
        """Aquatic biomes should appear ~61.8% (55/89) with ±12% tolerance."""
        creatures = _generate_all(v2_config, version_override="v2")
        biome_counts = Counter(c.classification.biome for c in creatures)

        aquatic_count = sum(biome_counts[b] for b in AQUATIC_BIOMES)
        aquatic_pct = aquatic_count / 1000 * 100

        assert aquatic_pct >= 50.0, f"Aquatic biomes too low: {aquatic_pct:.1f}%"
        assert aquatic_pct <= 75.0, f"Aquatic biomes too high: {aquatic_pct:.1f}%"

    def test_uniform_v1_has_no_biome_bias(self):
        """Without weights, no biome should exceed 3x expected uniform share."""
        config = get_config()
        creatures = _generate_all(config)
        biome_counts = Counter(c.classification.biome for c in creatures)

        expected_per_biome = 1000 / len(config.biomes)  # ~22.2
        for biome, count in biome_counts.items():
            assert count <= expected_per_biome * 3, (
                f"Biome {biome} appears {count} times, expected ~{expected_per_biome:.0f}"
            )

    def test_weighted_v2_more_aquatic_than_v1(self, v2_config):
        """v2 aquatic total should exceed v1 aquatic total."""
        v1_config = get_config()
        v1_creatures = _generate_all(v1_config, version_override="v1")
        v2_creatures = _generate_all(v2_config, version_override="v2")

        v1_aquatic = sum(1 for c in v1_creatures if c.classification.biome in AQUATIC_BIOMES)
        v2_aquatic = sum(1 for c in v2_creatures if c.classification.biome in AQUATIC_BIOMES)

        assert v2_aquatic > v1_aquatic, (
            f"v2 aquatic ({v2_aquatic}) should exceed v1 aquatic ({v1_aquatic})"
        )


# ── e) Rarity Distribution ──────────────────────────────────────────────────


class TestRarityDistribution1000:
    """Rarity matches configured weights within tolerance."""

    def test_rarity_proportions(self):
        config = get_config()
        creatures = _generate_all(config)
        rarity_counts = Counter(c.classification.rarity for c in creatures)

        # COMMON: 70% range -> expect 550-820
        assert 550 <= rarity_counts["COMMON"] <= 820, (
            f"COMMON count {rarity_counts['COMMON']} outside [550, 820]"
        )
        # UNCOMMON: 20% -> expect 100-300
        assert 100 <= rarity_counts["UNCOMMON"] <= 300, (
            f"UNCOMMON count {rarity_counts['UNCOMMON']} outside [100, 300]"
        )
        # RARE: 7% -> expect 20-130
        assert 20 <= rarity_counts["RARE"] <= 130, (
            f"RARE count {rarity_counts['RARE']} outside [20, 130]"
        )
        # EPIC + LEGENDARY should exist but be small
        assert rarity_counts["EPIC"] + rarity_counts["LEGENDARY"] >= 1, (
            "No EPIC or LEGENDARY in 1000 samples"
        )


# ── f) Biome-Species Constraints ─────────────────────────────────────────────


class TestBiomeSpeciesConstraints1000:
    """Every creature's species is valid for its biome."""

    def test_all_species_valid_for_biome_v1(self):
        config = get_config()
        creatures = _generate_all(config)
        for creature in creatures:
            eligible = config.get_species_for_biome(creature.classification.biome)
            assert creature.classification.species in eligible, (
                f"{creature.classification.species} not valid for "
                f"{creature.classification.biome}"
            )

    def test_all_species_valid_for_biome_v2(self, v2_config):
        """Biome-species constraints hold even with weighted biome selection."""
        creatures = _generate_all(v2_config, version_override="v2")
        for creature in creatures:
            eligible = v2_config.get_species_for_biome(creature.classification.biome)
            assert creature.classification.species in eligible

    def test_all_subtypes_valid(self):
        """Every creature's subtype is valid for its species+biome."""
        config = get_config()
        creatures = _generate_all(config)
        for creature in creatures:
            valid_subtypes = config.get_subtypes(
                creature.classification.species, creature.classification.biome
            )
            assert creature.classification.sub_type in valid_subtypes


# ── g) Stat Range Compliance ─────────────────────────────────────────────────


class TestStatRangeCompliance1000:
    """Every creature's stats within rarity bounds."""

    def test_all_stats_in_range_v1(self):
        config = get_config()
        creatures = _generate_all(config)
        for creature in creatures:
            stat_min, stat_max = config.get_stat_range(creature.classification.rarity)
            for stat_name in config.stat_names:
                val = getattr(creature.attributes, stat_name)
                assert stat_min <= val <= stat_max, (
                    f"{stat_name}={val} out of [{stat_min},{stat_max}] "
                    f"for {creature.classification.rarity}"
                )

    def test_all_stats_in_range_v2(self, v2_config):
        creatures = _generate_all(v2_config, version_override="v2")
        for creature in creatures:
            stat_min, stat_max = v2_config.get_stat_range(creature.classification.rarity)
            for stat_name in v2_config.stat_names:
                val = getattr(creature.attributes, stat_name)
                assert stat_min <= val <= stat_max


# ── h) Claimed Variants ─────────────────────────────────────────────────────


class TestClaimedVariants1000:
    """Claimed variants are always COMMON, different, and deterministic."""

    def test_claimed_variants_all_common(self):
        config = get_config()
        subset = BARCODE_CORPUS[:100]
        for code_type, raw_value in subset:
            normalised = normalise(code_type, raw_value)
            canonical_id = build_canonical_id(code_type, normalised)
            variant = generate_claimed_variant(
                code_type, raw_value, normalised, canonical_id, config
            )
            assert variant.classification.rarity == "COMMON"

    def test_claimed_variants_differ_from_originals(self):
        config = get_config()
        subset = BARCODE_CORPUS[:100]
        for code_type, raw_value in subset:
            normalised = normalise(code_type, raw_value)
            canonical_id = build_canonical_id(code_type, normalised)
            original = generate_creature(
                code_type, raw_value, normalised, canonical_id, config
            )
            variant = generate_claimed_variant(
                code_type, raw_value, normalised, canonical_id, config
            )
            assert original.identity.creature_id != variant.identity.creature_id

    def test_claimed_variants_are_deterministic(self):
        config = get_config()
        subset = BARCODE_CORPUS[:100]
        for code_type, raw_value in subset:
            normalised = normalise(code_type, raw_value)
            canonical_id = build_canonical_id(code_type, normalised)
            v1 = generate_claimed_variant(
                code_type, raw_value, normalised, canonical_id, config
            )
            v2 = generate_claimed_variant(
                code_type, raw_value, normalised, canonical_id, config
            )
            assert v1.identity.creature_id == v2.identity.creature_id
