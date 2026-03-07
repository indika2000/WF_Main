"""Unit tests for generation config loading and validation."""

import pytest

from app.services.config_loader import get_config


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
