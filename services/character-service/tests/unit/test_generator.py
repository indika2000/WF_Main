"""Unit tests for deterministic creature generation."""

import hashlib

import pytest

from app.services.config_loader import get_config
from app.services.generator import generate_creature, generate_claimed_variant


class TestDeterminism:
    """Verify same input always produces same output."""

    def test_same_input_same_creature(self):
        config = get_config()
        c1 = generate_creature("EAN_13", "5012345678900", "5012345678900",
                               "EAN_13|5012345678900|WILDERNESS_FRIENDS|v1", config)
        c2 = generate_creature("EAN_13", "5012345678900", "5012345678900",
                               "EAN_13|5012345678900|WILDERNESS_FRIENDS|v1", config)
        assert c1.identity.creature_id == c2.identity.creature_id
        assert c1.classification.rarity == c2.classification.rarity
        assert c1.classification.biome == c2.classification.biome
        assert c1.classification.species == c2.classification.species
        assert c1.presentation.name == c2.presentation.name
        assert c1.attributes.power == c2.attributes.power

    def test_different_input_different_creature(self):
        config = get_config()
        c1 = generate_creature("EAN_13", "5012345678900", "5012345678900",
                               "EAN_13|5012345678900|WILDERNESS_FRIENDS|v1", config)
        c2 = generate_creature("EAN_13", "5012345678901", "5012345678901",
                               "EAN_13|5012345678901|WILDERNESS_FRIENDS|v1", config)
        assert c1.identity.creature_id != c2.identity.creature_id

    def test_reroll_produces_different_creature(self):
        config = get_config()
        c0 = generate_creature("EAN_13", "5012345678900", "5012345678900",
                               "EAN_13|5012345678900|WILDERNESS_FRIENDS|v1", config,
                               reroll_iteration=0)
        c1 = generate_creature("EAN_13", "5012345678900", "5012345678900",
                               "EAN_13|5012345678900|WILDERNESS_FRIENDS|v1", config,
                               reroll_iteration=1)
        # Reroll should produce a different creature
        assert c0.identity.creature_id != c1.identity.creature_id

    def test_reroll_is_deterministic(self):
        config = get_config()
        c1 = generate_creature("EAN_13", "5012345678900", "5012345678900",
                               "EAN_13|5012345678900|WILDERNESS_FRIENDS|v1", config,
                               reroll_iteration=3)
        c2 = generate_creature("EAN_13", "5012345678900", "5012345678900",
                               "EAN_13|5012345678900|WILDERNESS_FRIENDS|v1", config,
                               reroll_iteration=3)
        assert c1.identity.creature_id == c2.identity.creature_id


class TestRarity:
    """Verify rarity distribution from byte values."""

    def test_rarity_from_config(self):
        config = get_config()
        # byte[0] % 100 maps to rarity
        assert config.get_rarity(0) == "COMMON"      # 0 % 100 = 0
        assert config.get_rarity(69) == "COMMON"      # 69 % 100 = 69
        assert config.get_rarity(70) == "UNCOMMON"     # 70 % 100 = 70
        assert config.get_rarity(89) == "UNCOMMON"     # 89 % 100 = 89
        assert config.get_rarity(90) == "RARE"         # 90 % 100 = 90
        assert config.get_rarity(96) == "RARE"         # 96 % 100 = 96
        assert config.get_rarity(97) == "EPIC"         # 97 % 100 = 97
        assert config.get_rarity(98) == "EPIC"         # 98 % 100 = 98
        assert config.get_rarity(99) == "LEGENDARY"    # 99 % 100 = 99

    def test_rarity_wraps_at_100(self):
        config = get_config()
        # byte value > 99 wraps via modulo
        assert config.get_rarity(100) == "COMMON"    # 100 % 100 = 0
        assert config.get_rarity(199) == "LEGENDARY"  # 199 % 100 = 99
        assert config.get_rarity(255) == "COMMON"     # 255 % 100 = 55


class TestBiomeConstraints:
    """Verify species are constrained by biome."""

    def test_creature_species_in_biome(self):
        config = get_config()
        # Generate many creatures and verify species-biome constraint
        for i in range(100):
            canonical = f"EAN_13|{str(i).zfill(13)}|WILDERNESS_FRIENDS|v1"
            creature = generate_creature(
                "EAN_13", str(i).zfill(13), str(i).zfill(13), canonical, config
            )
            biome = creature.classification.biome
            species = creature.classification.species
            eligible = config.get_species_for_biome(biome)
            assert species in eligible, (
                f"Species {species} not eligible for biome {biome}. "
                f"Eligible: {eligible}"
            )

    def test_subtype_valid_for_species_biome(self):
        config = get_config()
        for i in range(100):
            canonical = f"EAN_13|{str(i).zfill(13)}|WILDERNESS_FRIENDS|v1"
            creature = generate_creature(
                "EAN_13", str(i).zfill(13), str(i).zfill(13), canonical, config
            )
            species = creature.classification.species
            biome = creature.classification.biome
            sub_type = creature.classification.sub_type
            valid_subtypes = config.get_subtypes(species, biome)
            assert sub_type in valid_subtypes, (
                f"Subtype {sub_type} not valid for {species} in {biome}. "
                f"Valid: {valid_subtypes}"
            )


class TestStats:
    """Verify stats are within rarity-appropriate ranges."""

    def test_stats_within_rarity_range(self):
        config = get_config()
        for i in range(100):
            canonical = f"EAN_13|{str(i).zfill(13)}|WILDERNESS_FRIENDS|v1"
            creature = generate_creature(
                "EAN_13", str(i).zfill(13), str(i).zfill(13), canonical, config
            )
            rarity = creature.classification.rarity
            stat_min, stat_max = config.get_stat_range(rarity)
            attrs = creature.attributes
            for stat_name in config.stat_names:
                val = getattr(attrs, stat_name)
                assert stat_min <= val <= stat_max, (
                    f"Stat {stat_name}={val} out of range [{stat_min}, {stat_max}] "
                    f"for rarity {rarity}"
                )


class TestCreatureFields:
    """Verify all creature fields are populated correctly."""

    def test_all_fields_populated(self):
        config = get_config()
        creature = generate_creature(
            "EAN_13", "5012345678900", "5012345678900",
            "EAN_13|5012345678900|WILDERNESS_FRIENDS|v1", config
        )
        # Identity
        assert creature.identity.creature_id.startswith("WF-v1-")
        assert "|" in creature.identity.creature_signature

        # Source
        assert creature.source.code_type == "EAN_13"
        assert creature.source.raw_value == "5012345678900"
        assert "WILDERNESS_FRIENDS" in creature.source.canonical_id

        # Classification
        assert creature.classification.rarity in config.rarity_weights
        assert creature.classification.biome in config.biomes
        assert creature.classification.element in config.elements
        assert creature.classification.temperament in config.temperaments
        assert creature.classification.size in config.sizes
        assert creature.classification.variant in config.variants

        # Presentation
        assert len(creature.presentation.name) > 0
        assert creature.presentation.title.startswith("The ")
        assert creature.presentation.primary_color in config.primary_colors
        assert creature.presentation.secondary_color in config.secondary_colors
        assert creature.presentation.sigil in config.sigils
        assert creature.presentation.frame_style in config.frame_styles

        # Attributes
        assert creature.attributes.power >= 0
        assert creature.attributes.defense >= 0

        # Metadata
        assert creature.season == "v1"
        assert creature.generation_iteration == 0

    def test_signature_format(self):
        config = get_config()
        creature = generate_creature(
            "EAN_13", "5012345678900", "5012345678900",
            "EAN_13|5012345678900|WILDERNESS_FRIENDS|v1", config
        )
        parts = creature.identity.creature_signature.split("|")
        assert len(parts) == 8  # rarity|biome|species|sub_type|element|size|temperament|variant


class TestClaimedVariant:
    """Verify claimed variant generation."""

    def test_claimed_variant_is_common(self):
        config = get_config()
        variant = generate_claimed_variant(
            "EAN_13", "5012345678900", "5012345678900",
            "EAN_13|5012345678900|WILDERNESS_FRIENDS|v1", config
        )
        assert variant.classification.rarity == "COMMON"

    def test_claimed_variant_is_deterministic(self):
        config = get_config()
        v1 = generate_claimed_variant(
            "EAN_13", "5012345678900", "5012345678900",
            "EAN_13|5012345678900|WILDERNESS_FRIENDS|v1", config
        )
        v2 = generate_claimed_variant(
            "EAN_13", "5012345678900", "5012345678900",
            "EAN_13|5012345678900|WILDERNESS_FRIENDS|v1", config
        )
        assert v1.identity.creature_id == v2.identity.creature_id

    def test_claimed_variant_differs_from_original(self):
        config = get_config()
        original = generate_creature(
            "EAN_13", "5012345678900", "5012345678900",
            "EAN_13|5012345678900|WILDERNESS_FRIENDS|v1", config
        )
        variant = generate_claimed_variant(
            "EAN_13", "5012345678900", "5012345678900",
            "EAN_13|5012345678900|WILDERNESS_FRIENDS|v1", config
        )
        assert original.identity.creature_id != variant.identity.creature_id

    def test_claimed_variant_source_includes_suffix(self):
        config = get_config()
        variant = generate_claimed_variant(
            "EAN_13", "5012345678900", "5012345678900",
            "EAN_13|5012345678900|WILDERNESS_FRIENDS|v1", config
        )
        assert "|claimed_variant" in variant.source.canonical_id
