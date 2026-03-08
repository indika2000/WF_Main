"""Unit tests for generation config loading and validation."""

import os

import pytest
import yaml

from app.services.config_loader import GenerationConfig, get_config


class TestConfigLoading:
    """Verify the generation config loads and validates correctly."""

    def test_config_loaded(self):
        config = get_config()
        assert config is not None
        assert config.version == "v1"
        assert config.namespace == "WILDERNESS_FRIENDS"

    def test_has_all_biomes(self):
        config = get_config()
        assert len(config.biomes) >= 40  # Plan calls for ~45

    def test_has_all_species(self):
        config = get_config()
        assert len(config._species_ids) >= 60  # Plan calls for ~69

    def test_has_all_elements(self):
        config = get_config()
        assert len(config.elements) == 12

    def test_has_all_temperaments(self):
        config = get_config()
        assert len(config.temperaments) == 10

    def test_has_all_sizes(self):
        config = get_config()
        assert len(config.sizes) == 6

    def test_has_all_variants(self):
        config = get_config()
        assert len(config.variants) == 25

    def test_rarity_weights_cover_0_to_99(self):
        config = get_config()
        covered = set()
        for rarity, weight in config.rarity_weights.items():
            for i in range(weight["min"], weight["max"] + 1):
                covered.add(i)
        assert covered == set(range(100))

    def test_every_biome_has_species(self):
        config = get_config()
        for biome in config.biomes:
            species = config.get_species_for_biome(biome)
            assert len(species) > 0, f"Biome {biome} has no species"

    def test_every_species_in_at_least_one_biome(self):
        config = get_config()
        species_with_biomes = set()
        for biome, species_list in config.biome_species_map.items():
            for sp in species_list:
                species_with_biomes.add(sp)
        for sp_id in config._species_ids:
            assert sp_id in species_with_biomes, (
                f"Species {sp_id} has no biome assignment"
            )

    def test_every_species_has_subtypes(self):
        config = get_config()
        for sp_id in config._species_ids:
            subtypes = config.get_subtypes(sp_id, "NONEXISTENT_BIOME")
            assert len(subtypes) > 0, (
                f"Species {sp_id} has no subtypes (not even DEFAULT)"
            )

    def test_supply_caps_defined_for_all_rarities(self):
        config = get_config()
        for rarity in config.rarity_weights:
            assert rarity in config.supply_caps

    def test_stat_ranges_defined_for_all_rarities(self):
        config = get_config()
        for rarity in config.rarity_weights:
            stat_min, stat_max = config.get_stat_range(rarity)
            assert stat_min < stat_max
            assert stat_min >= 0
            assert stat_max <= 100

    def test_collision_policy_defined_for_all_rarities(self):
        config = get_config()
        valid_policies = {
            "ALLOW", "ALLOW_IF_STATS_DIFFER",
            "REROLL_ON_SIGNATURE_MATCH", "REROLL_ON_ANY_ARCHETYPE_MATCH",
        }
        for rarity in config.rarity_weights:
            policy = config.collision_policy[rarity]
            assert policy in valid_policies, (
                f"Invalid policy '{policy}' for {rarity}"
            )

    def test_common_is_unlimited(self):
        config = get_config()
        assert config.supply_caps["COMMON"] is None

    def test_legendary_has_lowest_cap(self):
        config = get_config()
        caps = {r: c for r, c in config.supply_caps.items() if c is not None}
        legendary_cap = caps["LEGENDARY"]
        for rarity, cap in caps.items():
            if rarity != "LEGENDARY":
                assert cap >= legendary_cap


class TestBiomeWeights:
    """Verify weighted biome selection logic."""

    def test_v1_has_no_biome_weights(self):
        config = get_config()
        assert config.biome_weights is None

    def test_get_biome_uniform_without_weights(self):
        """Without biome_weights, get_biome behaves identically to modulo pick."""
        config = get_config()
        for byte_val in range(256):
            expected = config.biomes[byte_val % len(config.biomes)]
            assert config.get_biome(byte_val) == expected

    def test_get_biome_weighted_deterministic(self, v2_config):
        """Same byte value always returns same biome with weights."""
        for byte_val in range(256):
            result1 = v2_config.get_biome(byte_val)
            result2 = v2_config.get_biome(byte_val)
            assert result1 == result2

    def test_weighted_biome_coverage(self, v2_config):
        """All biomes should be reachable with weights (no biome has 0 chance)."""
        reachable = set()
        for byte_val in range(256):
            reachable.add(v2_config.get_biome(byte_val))
        assert reachable == set(v2_config.biomes), (
            f"Unreachable biomes: {set(v2_config.biomes) - reachable}"
        )

    def test_invalid_biome_in_weights_raises(self):
        """biome_weights with unknown biome should raise ValueError."""
        v1_path = os.environ["GENERATION_CONFIG_PATH"]
        with open(v1_path) as f:
            data = yaml.safe_load(f)
        data["biome_weights"] = {"NONEXISTENT_BIOME": 5}
        with pytest.raises(ValueError, match="not in biomes list"):
            GenerationConfig(data)

    def test_zero_weight_raises(self):
        """Weight of 0 should raise ValueError."""
        v1_path = os.environ["GENERATION_CONFIG_PATH"]
        with open(v1_path) as f:
            data = yaml.safe_load(f)
        data["biome_weights"] = {"OCEAN": 0}
        with pytest.raises(ValueError, match="positive integer"):
            GenerationConfig(data)

    def test_v2_config_matches_v1_structure(self, v2_config):
        """v2 test config should match v1 except version and biome_weights."""
        v1_config = get_config()
        assert v2_config.version == "v2"
        assert v1_config.version == "v1"
        assert v2_config.biomes == v1_config.biomes
        assert v2_config.biome_species_map == v1_config.biome_species_map
        assert v2_config._species_ids == v1_config._species_ids
        assert v2_config.elements == v1_config.elements
        assert v2_config.rarity_weights == v1_config.rarity_weights


class TestWorldTemplates:
    """Verify world-flexible template configuration."""

    def test_v1_default_id_prefix(self):
        config = get_config()
        assert config.id_prefix == "WF"

    def test_v1_default_name_template(self):
        config = get_config()
        assert config.name_template == "{variant} {sub_type}"

    def test_v1_default_title_template(self):
        config = get_config()
        assert config.title_template == "The {role} of {domain}"

    def test_cyber_custom_id_prefix(self, cyber_config):
        assert cyber_config.id_prefix == "CF"

    def test_cyber_custom_title_template(self, cyber_config):
        assert cyber_config.title_template == "{role} of {domain}"

    def test_custom_templates_in_raw_config(self):
        """Custom templates can be set in YAML and are parsed correctly."""
        v1_path = os.environ["GENERATION_CONFIG_PATH"]
        with open(v1_path) as f:
            data = yaml.safe_load(f)
        data["id_prefix"] = "TEST"
        data["name_template"] = "{species} Unit {variant}"
        data["title_template"] = "{role} — {domain}"
        config = GenerationConfig(data)
        assert config.id_prefix == "TEST"
        assert config.name_template == "{species} Unit {variant}"
        assert config.title_template == "{role} — {domain}"
