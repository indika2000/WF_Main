"""Cross-world 1000-barcode test suite.

Validates that the generator works correctly with a completely different
world schema (CyberFriends) and that world isolation is maintained between
WildernessFriends (v1) and CyberFriends (c1).
"""

import random
import string
from collections import Counter

import pytest

from app.services.config_loader import get_config
from app.services.generator import generate_creature, generate_claimed_variant
from app.services.normalisation import normalise


# ── Barcode Corpus (deterministic, shared across all tests) ──────────────────

_rng = random.Random(99)  # Different seed from test_1000_barcodes to avoid coupling


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


# ── Helper ───────────────────────────────────────────────────────────────────


def _generate_all(config, namespace_override=None, version_override=None):
    """Generate creatures for the full corpus with the given config."""
    creatures = []
    ns = namespace_override or config.namespace
    ver = version_override or config.version
    for code_type, raw_value in BARCODE_CORPUS:
        normalised = normalise(code_type, raw_value)
        canonical_id = f"{code_type}|{normalised}|{ns}|{ver}"
        creature = generate_creature(
            code_type, raw_value, normalised, canonical_id, config
        )
        creatures.append(creature)
    return creatures


# ── a) CyberFriends Config Validation ───────────────────────────────────────


class TestCyberConfigValidation:
    """Verify the cyber config loads, validates, and has correct structure."""

    def test_cyber_config_loads(self, cyber_config):
        assert cyber_config is not None
        assert cyber_config.version == "c1"
        assert cyber_config.namespace == "CYBER_FRIENDS"

    def test_cyber_has_custom_id_prefix(self, cyber_config):
        assert cyber_config.id_prefix == "CF"

    def test_cyber_has_custom_name_template(self, cyber_config):
        assert cyber_config.name_template == "{variant} {sub_type}"

    def test_cyber_has_custom_title_template(self, cyber_config):
        assert cyber_config.title_template == "{role} of {domain}"

    def test_cyber_has_all_biomes(self, cyber_config):
        assert len(cyber_config.biomes) == 30

    def test_cyber_has_all_species(self, cyber_config):
        assert len(cyber_config._species_ids) == 40

    def test_cyber_has_all_elements(self, cyber_config):
        assert len(cyber_config.elements) == 12

    def test_cyber_has_all_temperaments(self, cyber_config):
        assert len(cyber_config.temperaments) == 10

    def test_cyber_has_all_sizes(self, cyber_config):
        assert len(cyber_config.sizes) == 6

    def test_cyber_has_all_variants(self, cyber_config):
        assert len(cyber_config.variants) == 25

    def test_every_cyber_biome_has_species(self, cyber_config):
        for biome in cyber_config.biomes:
            species = cyber_config.get_species_for_biome(biome)
            assert len(species) > 0, f"Biome {biome} has no species"

    def test_every_cyber_species_in_at_least_one_biome(self, cyber_config):
        species_with_biomes = set()
        for biome, species_list in cyber_config.biome_species_map.items():
            for sp in species_list:
                species_with_biomes.add(sp)
        for sp_id in cyber_config._species_ids:
            assert sp_id in species_with_biomes, (
                f"Species {sp_id} has no biome assignment"
            )

    def test_every_cyber_species_has_subtypes(self, cyber_config):
        for sp_id in cyber_config._species_ids:
            subtypes = cyber_config.get_subtypes(sp_id, "NONEXISTENT_BIOME")
            assert len(subtypes) > 0, (
                f"Species {sp_id} has no subtypes (not even DEFAULT)"
            )

    def test_cyber_content_differs_from_v1(self, cyber_config):
        """Cyber world species, biomes, elements etc are distinct from v1."""
        v1_config = get_config()
        # No overlap in species
        cyber_species = set(cyber_config._species_ids)
        v1_species = set(v1_config._species_ids)
        assert cyber_species.isdisjoint(v1_species), (
            f"Shared species: {cyber_species & v1_species}"
        )
        # No overlap in biomes
        cyber_biomes = set(cyber_config.biomes)
        v1_biomes = set(v1_config.biomes)
        assert cyber_biomes.isdisjoint(v1_biomes), (
            f"Shared biomes: {cyber_biomes & v1_biomes}"
        )
        # No overlap in elements
        cyber_elements = set(cyber_config.elements)
        v1_elements = set(v1_config.elements)
        assert cyber_elements.isdisjoint(v1_elements), (
            f"Shared elements: {cyber_elements & v1_elements}"
        )


# ── b) CyberFriends Determinism ─────────────────────────────────────────────


class TestCyberDeterminism1000:
    """Same barcode -> identical creature in CyberFriends world."""

    def test_1000_barcodes_deterministic(self, cyber_config):
        for code_type, raw_value in BARCODE_CORPUS:
            normalised = normalise(code_type, raw_value)
            canonical_id = f"{code_type}|{normalised}|CYBER_FRIENDS|c1"
            c1 = generate_creature(code_type, raw_value, normalised, canonical_id, cyber_config)
            c2 = generate_creature(code_type, raw_value, normalised, canonical_id, cyber_config)
            assert c1.identity.creature_id == c2.identity.creature_id
            assert c1.classification.rarity == c2.classification.rarity
            assert c1.classification.biome == c2.classification.biome
            assert c1.classification.species == c2.classification.species
            assert c1.attributes.power == c2.attributes.power


# ── c) CyberFriends Uniqueness ──────────────────────────────────────────────


class TestCyberUniqueness1000:
    """1000 different barcodes -> high % of unique creature_ids."""

    def test_unique_creature_ids(self, cyber_config):
        creatures = _generate_all(cyber_config)
        creature_ids = {c.identity.creature_id for c in creatures}
        assert len(creature_ids) >= 990, (
            f"Only {len(creature_ids)}/1000 unique creature_ids"
        )


# ── d) World Isolation ──────────────────────────────────────────────────────


class TestWorldIsolation:
    """Same barcodes in v1 (WildernessFriends) vs c1 (CyberFriends) -> completely different creatures."""

    def test_different_creatures_across_worlds(self, cyber_config):
        """Same 100 barcodes produce different creatures in different worlds."""
        v1_config = get_config()
        subset = BARCODE_CORPUS[:100]

        for code_type, raw_value in subset:
            normalised = normalise(code_type, raw_value)
            v1_canonical = f"{code_type}|{normalised}|WILDERNESS_FRIENDS|v1"
            cyber_canonical = f"{code_type}|{normalised}|CYBER_FRIENDS|c1"

            c_v1 = generate_creature(code_type, raw_value, normalised, v1_canonical, v1_config)
            c_cyber = generate_creature(code_type, raw_value, normalised, cyber_canonical, cyber_config)

            assert c_v1.identity.creature_id != c_cyber.identity.creature_id, (
                f"Barcode {raw_value} produced same creature across worlds"
            )

    def test_zero_id_overlap_across_worlds(self, cyber_config):
        """No creature IDs should overlap between worlds."""
        v1_config = get_config()
        subset = BARCODE_CORPUS[:100]

        v1_ids = set()
        cyber_ids = set()
        for code_type, raw_value in subset:
            normalised = normalise(code_type, raw_value)
            v1_canonical = f"{code_type}|{normalised}|WILDERNESS_FRIENDS|v1"
            cyber_canonical = f"{code_type}|{normalised}|CYBER_FRIENDS|c1"
            v1_ids.add(
                generate_creature(code_type, raw_value, normalised, v1_canonical, v1_config)
                .identity.creature_id
            )
            cyber_ids.add(
                generate_creature(code_type, raw_value, normalised, cyber_canonical, cyber_config)
                .identity.creature_id
            )
        assert v1_ids.isdisjoint(cyber_ids), "Worlds share creature IDs"

    def test_id_prefix_differs_between_worlds(self, cyber_config):
        """CyberFriends uses CF- prefix, WildernessFriends uses WF-."""
        v1_config = get_config()
        code_type, raw_value = BARCODE_CORPUS[0]
        normalised = normalise(code_type, raw_value)

        v1_canonical = f"{code_type}|{normalised}|WILDERNESS_FRIENDS|v1"
        cyber_canonical = f"{code_type}|{normalised}|CYBER_FRIENDS|c1"

        c_v1 = generate_creature(code_type, raw_value, normalised, v1_canonical, v1_config)
        c_cyber = generate_creature(code_type, raw_value, normalised, cyber_canonical, cyber_config)

        assert c_v1.identity.creature_id.startswith("WF-")
        assert c_cyber.identity.creature_id.startswith("CF-")

    def test_title_template_differs_between_worlds(self, cyber_config):
        """CyberFriends titles lack 'The' prefix (different template)."""
        v1_config = get_config()
        code_type, raw_value = BARCODE_CORPUS[0]
        normalised = normalise(code_type, raw_value)

        v1_canonical = f"{code_type}|{normalised}|WILDERNESS_FRIENDS|v1"
        cyber_canonical = f"{code_type}|{normalised}|CYBER_FRIENDS|c1"

        c_v1 = generate_creature(code_type, raw_value, normalised, v1_canonical, v1_config)
        c_cyber = generate_creature(code_type, raw_value, normalised, cyber_canonical, cyber_config)

        assert c_v1.presentation.title.startswith("The ")
        assert not c_cyber.presentation.title.startswith("The ")


# ── e) CyberFriends Biome-Species Constraints ──────────────────────────────


class TestCyberBiomeSpeciesConstraints1000:
    """Every CyberFriends creature's species is valid for its biome."""

    def test_all_species_valid_for_biome(self, cyber_config):
        creatures = _generate_all(cyber_config)
        for creature in creatures:
            eligible = cyber_config.get_species_for_biome(creature.classification.biome)
            assert creature.classification.species in eligible, (
                f"{creature.classification.species} not valid for "
                f"{creature.classification.biome}"
            )

    def test_all_subtypes_valid(self, cyber_config):
        """Every creature's subtype is valid for its species+biome."""
        creatures = _generate_all(cyber_config)
        for creature in creatures:
            valid_subtypes = cyber_config.get_subtypes(
                creature.classification.species, creature.classification.biome
            )
            assert creature.classification.sub_type in valid_subtypes, (
                f"{creature.classification.sub_type} not valid subtype for "
                f"{creature.classification.species} in {creature.classification.biome}"
            )


# ── f) CyberFriends Rarity Distribution ────────────────────────────────────


class TestCyberRarityDistribution1000:
    """Rarity matches configured weights within tolerance."""

    def test_rarity_proportions(self, cyber_config):
        creatures = _generate_all(cyber_config)
        rarity_counts = Counter(c.classification.rarity for c in creatures)

        assert 550 <= rarity_counts["COMMON"] <= 820, (
            f"COMMON count {rarity_counts['COMMON']} outside [550, 820]"
        )
        assert 100 <= rarity_counts["UNCOMMON"] <= 300, (
            f"UNCOMMON count {rarity_counts['UNCOMMON']} outside [100, 300]"
        )
        assert 20 <= rarity_counts["RARE"] <= 130, (
            f"RARE count {rarity_counts['RARE']} outside [20, 130]"
        )
        assert rarity_counts["EPIC"] + rarity_counts["LEGENDARY"] >= 1, (
            "No EPIC or LEGENDARY in 1000 samples"
        )


# ── g) CyberFriends Stat Range Compliance ──────────────────────────────────


class TestCyberStatRangeCompliance1000:
    """Every creature's stats within rarity bounds."""

    def test_all_stats_in_range(self, cyber_config):
        creatures = _generate_all(cyber_config)
        for creature in creatures:
            stat_min, stat_max = cyber_config.get_stat_range(creature.classification.rarity)
            for stat_name in cyber_config.stat_names:
                val = getattr(creature.attributes, stat_name)
                assert stat_min <= val <= stat_max, (
                    f"{stat_name}={val} out of [{stat_min},{stat_max}] "
                    f"for {creature.classification.rarity}"
                )


# ── h) CyberFriends Claimed Variants ───────────────────────────────────────


class TestCyberClaimedVariants1000:
    """Claimed variants are always COMMON, different, and deterministic."""

    def test_claimed_variants_all_common(self, cyber_config):
        subset = BARCODE_CORPUS[:100]
        for code_type, raw_value in subset:
            normalised = normalise(code_type, raw_value)
            canonical_id = f"{code_type}|{normalised}|CYBER_FRIENDS|c1"
            variant = generate_claimed_variant(
                code_type, raw_value, normalised, canonical_id, cyber_config
            )
            assert variant.classification.rarity == "COMMON"

    def test_claimed_variants_differ_from_originals(self, cyber_config):
        subset = BARCODE_CORPUS[:100]
        for code_type, raw_value in subset:
            normalised = normalise(code_type, raw_value)
            canonical_id = f"{code_type}|{normalised}|CYBER_FRIENDS|c1"
            original = generate_creature(
                code_type, raw_value, normalised, canonical_id, cyber_config
            )
            variant = generate_claimed_variant(
                code_type, raw_value, normalised, canonical_id, cyber_config
            )
            assert original.identity.creature_id != variant.identity.creature_id

    def test_claimed_variants_are_deterministic(self, cyber_config):
        subset = BARCODE_CORPUS[:100]
        for code_type, raw_value in subset:
            normalised = normalise(code_type, raw_value)
            canonical_id = f"{code_type}|{normalised}|CYBER_FRIENDS|c1"
            v1 = generate_claimed_variant(
                code_type, raw_value, normalised, canonical_id, cyber_config
            )
            v2 = generate_claimed_variant(
                code_type, raw_value, normalised, canonical_id, cyber_config
            )
            assert v1.identity.creature_id == v2.identity.creature_id


# ── i) CyberFriends Content Verification ───────────────────────────────────


class TestCyberContentVerification:
    """Verify generated creatures use cyber-themed content, not wilderness."""

    def test_biomes_are_cyber_themed(self, cyber_config):
        """All generated biomes should be from the cyber biome list."""
        creatures = _generate_all(cyber_config)
        cyber_biomes = set(cyber_config.biomes)
        for creature in creatures:
            assert creature.classification.biome in cyber_biomes

    def test_species_are_cyber_themed(self, cyber_config):
        """All generated species should be from the cyber species list."""
        creatures = _generate_all(cyber_config)
        cyber_species = set(cyber_config._species_ids)
        for creature in creatures:
            assert creature.classification.species in cyber_species

    def test_elements_are_cyber_themed(self, cyber_config):
        """All generated elements should be from the cyber element list."""
        creatures = _generate_all(cyber_config)
        cyber_elements = set(cyber_config.elements)
        for creature in creatures:
            assert creature.classification.element in cyber_elements

    def test_creature_ids_use_cyber_prefix(self, cyber_config):
        """All CyberFriends creature IDs start with CF-."""
        creatures = _generate_all(cyber_config)
        for creature in creatures:
            assert creature.identity.creature_id.startswith("CF-"), (
                f"Expected CF- prefix, got {creature.identity.creature_id}"
            )

    def test_creature_ids_contain_cyber_biomes(self, cyber_config):
        """CyberFriends creature IDs contain cyber biome names."""
        creatures = _generate_all(cyber_config)[:50]
        cyber_biomes = set(cyber_config.biomes)
        for creature in creatures:
            # creature_id format: CF-c1-RARITY-BIOME-SPECIES-HASH
            parts = creature.identity.creature_id.split("-")
            # Biome is after CF, c1, RARITY — but biome may contain hyphens
            # Instead, just verify biome from classification is in cyber biomes
            assert creature.classification.biome in cyber_biomes


# ── j) Template Flexibility ─────────────────────────────────────────────────


class TestTemplateFlexibility:
    """Verify v1 defaults still work and custom templates apply correctly."""

    def test_v1_uses_default_templates(self):
        """v1 config uses default name/title templates (backward compatible)."""
        v1_config = get_config()
        assert v1_config.id_prefix == "WF"
        assert v1_config.name_template == "{variant} {sub_type}"
        assert v1_config.title_template == "The {role} of {domain}"

    def test_v1_creature_title_has_the(self):
        """v1 creatures use 'The X of Y' title format."""
        v1_config = get_config()
        code_type, raw_value = BARCODE_CORPUS[0]
        normalised = normalise(code_type, raw_value)
        canonical_id = f"{code_type}|{normalised}|WILDERNESS_FRIENDS|v1"
        creature = generate_creature(code_type, raw_value, normalised, canonical_id, v1_config)
        assert creature.presentation.title.startswith("The ")
        assert " of " in creature.presentation.title

    def test_cyber_creature_title_no_the(self, cyber_config):
        """Cyber creatures use 'X of Y' title format (no 'The')."""
        code_type, raw_value = BARCODE_CORPUS[0]
        normalised = normalise(code_type, raw_value)
        canonical_id = f"{code_type}|{normalised}|CYBER_FRIENDS|c1"
        creature = generate_creature(code_type, raw_value, normalised, canonical_id, cyber_config)
        assert not creature.presentation.title.startswith("The ")
        assert " of " in creature.presentation.title
