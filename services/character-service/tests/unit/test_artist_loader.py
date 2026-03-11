"""Unit tests for artist_loader — artist config and assignment logic."""

import pytest

from app.services.artist_loader import get_artist_registry


class TestArtistRegistry:
    def test_loads_four_artists(self):
        registry = get_artist_registry()
        assert len(registry.artists) == 4

    def test_artist_has_required_fields(self):
        registry = get_artist_registry()
        for artist_id, config in registry.artists.items():
            assert config.artist_id == artist_id
            assert config.name
            assert config.title
            assert config.style_directive
            assert isinstance(config.biome_affinities, list)
            assert isinstance(config.family_affinities, list)


class TestArtistAssignment:
    def test_forest_biome_gets_kaelith(self):
        """FOREST is in Kaelith's biome affinities."""
        registry = get_artist_registry()
        artist_id = registry.assign_artist("FOREST", "BEAST", "test-canonical-1")
        assert artist_id == "kaelith"

    def test_volcanic_biome_gets_thornforge(self):
        """VOLCANIC_MOUNTAIN is in Thornforge's biome affinities."""
        registry = get_artist_registry()
        artist_id = registry.assign_artist("VOLCANIC_MOUNTAIN", "NATURE_SPIRIT", "test-canonical-1")
        assert artist_id == "thornforge"

    def test_ocean_biome_gets_mistweaver(self):
        """OCEAN is in Mistweaver's biome affinities."""
        registry = get_artist_registry()
        artist_id = registry.assign_artist("OCEAN", "NATURE_SPIRIT", "test-canonical-1")
        assert artist_id == "mistweaver"

    def test_sky_biome_gets_solara(self):
        """SKY_REALM is in Solara's biome affinities."""
        registry = get_artist_registry()
        artist_id = registry.assign_artist("SKY_REALM", "BEAST", "test-canonical-1")
        assert artist_id == "solara"

    def test_family_fallback_when_no_biome_match(self):
        """When biome doesn't match any artist, use family affinity."""
        registry = get_artist_registry()
        # VOID_DIMENSION doesn't match any biome, DRAGON is Thornforge's family
        artist_id = registry.assign_artist("VOID_DIMENSION", "DRAGON", "test-canonical-1")
        assert artist_id == "thornforge"

    def test_deterministic_assignment(self):
        """Same canonical_id always gets the same artist."""
        registry = get_artist_registry()
        a1 = registry.assign_artist("UNKNOWN_BIOME", "UNKNOWN_FAMILY", "canonical-abc")
        a2 = registry.assign_artist("UNKNOWN_BIOME", "UNKNOWN_FAMILY", "canonical-abc")
        assert a1 == a2

    def test_different_canonical_ids_can_differ(self):
        """Different canonical IDs may get different artists (via hash tiebreaker)."""
        registry = get_artist_registry()
        results = set()
        for i in range(100):
            artist_id = registry.assign_artist("UNKNOWN", "UNKNOWN", f"canonical-{i}")
            results.add(artist_id)
        # With 100 different IDs and 4 artists, we should see at least 2 different artists
        assert len(results) >= 2
