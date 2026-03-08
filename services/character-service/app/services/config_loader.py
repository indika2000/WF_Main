"""Load and validate generation_v1.yml at startup."""

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class GenerationConfig:
    """Parsed, validated, and indexed generation config."""

    def __init__(self, data: dict[str, Any]):
        self.version: str = data["version"]
        self.namespace: str = data["namespace"]

        # Rarity
        self.rarity_weights: dict[str, dict] = data["rarity_weights"]
        self.supply_caps: dict[str, int | None] = data["supply_caps"]
        self.collision_policy: dict[str, str] = data["collision_policy"]
        self.max_reroll_attempts: int = data.get("max_reroll_attempts", 10)
        self.stat_ranges: dict[str, dict] = data["stat_ranges"]
        self.stat_names: list[str] = data["stat_names"]

        # Enums
        self.biomes: list[str] = data["biomes"]
        self.species_list: list[dict] = data["species"]
        self.elements: list[str] = data["elements"]
        self.temperaments: list[str] = data["temperaments"]
        self.sizes: list[str] = data["sizes"]
        self.variants: list[str] = data["variants"]
        self.primary_colors: list[str] = data["primary_colors"]
        self.secondary_colors: list[str] = data["secondary_colors"]
        self.sigils: list[str] = data["sigils"]
        self.frame_styles: list[str] = data["frame_styles"]
        self.roles: list[str] = data["roles"]
        self.domains: list[str] = data["domains"]

        # Maps
        self.biome_species_map: dict[str, list[str]] = data["biome_species_map"]
        self.subtype_map: dict[str, dict[str, list[str]]] = data["subtype_map"]

        # Optional biome weights for seasonal theming
        raw_weights = data.get("biome_weights", None)
        if raw_weights is not None:
            self.biome_weights: dict[str, int] | None = raw_weights
            # Pre-compute cumulative weight table (iterate biomes list for determinism)
            self._biome_cumulative: list[tuple[int, str]] = []
            cumulative = 0
            for biome in self.biomes:
                weight = self.biome_weights.get(biome, 1)  # default weight 1
                cumulative += weight
                self._biome_cumulative.append((cumulative, biome))
            self._biome_total_weight: int = cumulative
        else:
            self.biome_weights = None
            self._biome_cumulative = []
            self._biome_total_weight = 0

        # Build lookup indexes
        self._species_ids: list[str] = [s["id"] for s in self.species_list]
        self._species_family: dict[str, str] = {
            s["id"]: s["family"] for s in self.species_list
        }

        self._validate()

    def _validate(self) -> None:
        """Validate referential integrity of the config."""
        species_set = set(self._species_ids)

        # Every species in biome map must be in species list
        for biome, species_list in self.biome_species_map.items():
            if biome not in self.biomes:
                raise ValueError(f"Biome '{biome}' in biome_species_map not in biomes list")
            for sp in species_list:
                if sp not in species_set:
                    raise ValueError(
                        f"Species '{sp}' in biome_species_map[{biome}] not in species list"
                    )

        # Every biome must have species
        for biome in self.biomes:
            if biome not in self.biome_species_map:
                raise ValueError(f"Biome '{biome}' has no entry in biome_species_map")

        # Every species in subtype_map must be in species list
        for sp in self.subtype_map:
            if sp not in species_set:
                raise ValueError(f"Species '{sp}' in subtype_map not in species list")

        # Every rarity must have stat_ranges, supply_caps, collision_policy
        for rarity in self.rarity_weights:
            if rarity not in self.stat_ranges:
                raise ValueError(f"Rarity '{rarity}' missing from stat_ranges")
            if rarity not in self.supply_caps:
                raise ValueError(f"Rarity '{rarity}' missing from supply_caps")
            if rarity not in self.collision_policy:
                raise ValueError(f"Rarity '{rarity}' missing from collision_policy")

        # Validate biome weights if present
        if self.biome_weights is not None:
            for biome in self.biome_weights:
                if biome not in self.biomes:
                    raise ValueError(
                        f"Biome '{biome}' in biome_weights not in biomes list"
                    )
            for biome, weight in self.biome_weights.items():
                if not isinstance(weight, int) or weight < 1:
                    raise ValueError(
                        f"Weight for biome '{biome}' must be a positive integer, got {weight}"
                    )

        logger.info(
            "Config validated: %d biomes, %d species, %d subtype entries%s",
            len(self.biomes),
            len(self._species_ids),
            len(self.subtype_map),
            f", biome_weights active (total={self._biome_total_weight})"
            if self.biome_weights
            else "",
        )

    def get_rarity(self, byte_val: int) -> str:
        """Map a byte value (0-255) to a rarity tier."""
        roll = byte_val % 100
        for rarity, weight in self.rarity_weights.items():
            if weight["min"] <= roll <= weight["max"]:
                return rarity
        return "COMMON"

    def get_biome(self, byte_val: int) -> str:
        """Get biome from byte value, using weights if configured."""
        if self.biome_weights is None:
            return self.biomes[byte_val % len(self.biomes)]
        position = byte_val % self._biome_total_weight
        for cumulative_threshold, biome in self._biome_cumulative:
            if position < cumulative_threshold:
                return biome
        return self._biome_cumulative[-1][1]

    def get_species_for_biome(self, biome: str) -> list[str]:
        """Get eligible species for a biome."""
        return self.biome_species_map.get(biome, [])

    def get_family(self, species: str) -> str:
        """Get the family for a species."""
        return self._species_family.get(species, "UNKNOWN")

    def get_subtypes(self, species: str, biome: str) -> list[str]:
        """Get subtypes for a species in a biome, falling back to DEFAULT."""
        species_map = self.subtype_map.get(species, {})
        return species_map.get(biome, species_map.get("DEFAULT", [species]))

    def get_stat_range(self, rarity: str) -> tuple[int, int]:
        """Get (min, max) stat range for a rarity."""
        r = self.stat_ranges[rarity]
        return r["min"], r["max"]

    def get_rarities_ordered(self) -> list[str]:
        """Get rarities in order from highest to lowest."""
        return list(self.rarity_weights.keys())


# Module-level singleton (set on startup)
_config: GenerationConfig | None = None


def load_config(path: str) -> GenerationConfig:
    """Load and validate the generation config from a YAML file."""
    global _config
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    _config = GenerationConfig(data)
    logger.info("Loaded generation config v%s from %s", _config.version, path)
    return _config


def get_config() -> GenerationConfig:
    """Get the loaded generation config. Raises if not loaded."""
    if _config is None:
        raise RuntimeError("Generation config not loaded — call load_config() first")
    return _config
