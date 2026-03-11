"""Load and manage artist persona configuration."""

import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ArtistConfig:
    """A single artist persona."""

    artist_id: str
    name: str
    title: str
    style_directive: str
    biome_affinities: list[str]
    family_affinities: list[str]
    # Loaded at startup from config/artists/{artist_id}/*.png
    reference_image_bytes: list[bytes] = field(default_factory=list, repr=False)


class ArtistRegistry:
    """Registry of all artist personas with assignment logic."""

    def __init__(self, artists: dict[str, ArtistConfig]):
        self.artists = artists
        self._artist_ids = list(artists.keys())

    def get(self, artist_id: str) -> ArtistConfig | None:
        return self.artists.get(artist_id)

    def assign_artist(self, biome: str, family: str, canonical_id: str) -> str:
        """Assign an artist based on biome/family affinities with hash tiebreaker.

        Priority:
        1. Biome affinity match (biome is most visually impactful)
        2. Family affinity match
        3. All artists eligible (no match)
        4. Deterministic tiebreaker using canonical_id hash byte[2]
        """
        candidates = []

        # Check biome affinities first
        for artist_id, config in self.artists.items():
            if biome in config.biome_affinities:
                candidates.append(artist_id)

        # If no biome match, check family affinities
        if not candidates:
            for artist_id, config in self.artists.items():
                if family in config.family_affinities:
                    candidates.append(artist_id)

        # If still no match, all artists are candidates
        if not candidates:
            candidates = self._artist_ids

        # Deterministic selection using hash byte[2]
        hash_bytes = hashlib.sha256(canonical_id.encode()).digest()
        index = hash_bytes[2] % len(candidates)
        return candidates[index]


# Module-level singleton
_registry: ArtistRegistry | None = None


def _load_reference_images(artist_id: str, config_dir: Path) -> list[bytes]:
    """Load reference image files from config/artists/{artist_id}/."""
    artist_dir = config_dir / "artists" / artist_id
    if not artist_dir.is_dir():
        return []

    image_bytes: list[bytes] = []
    for img_path in sorted(artist_dir.iterdir()):
        if img_path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
            image_bytes.append(img_path.read_bytes())
            logger.info(
                "Loaded reference image: %s (%d bytes)",
                img_path.name,
                len(image_bytes[-1]),
            )
    return image_bytes


def load_artists(path: str) -> ArtistRegistry:
    """Load artist config from YAML and return a registry."""
    global _registry
    config_dir = Path(path).parent

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    artists: dict[str, ArtistConfig] = {}
    for artist_id, artist_data in data["artists"].items():
        ref_bytes = _load_reference_images(artist_id, config_dir)
        artists[artist_id] = ArtistConfig(
            artist_id=artist_id,
            name=artist_data["name"],
            title=artist_data["title"],
            style_directive=artist_data["style_directive"].strip(),
            biome_affinities=artist_data.get("biome_affinities", []),
            family_affinities=artist_data.get("family_affinities", []),
            reference_image_bytes=ref_bytes,
        )

    _registry = ArtistRegistry(artists)
    logger.info("Loaded %d artist personas", len(artists))
    return _registry


def get_artist_registry() -> ArtistRegistry:
    """Get the loaded artist registry. Raises if not loaded."""
    if _registry is None:
        raise RuntimeError("Artist config not loaded — call load_artists() first")
    return _registry
