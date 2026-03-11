"""Unit tests for prompt_builder — stat-to-visual mapping and prompt composition."""

import pytest

from app.models.creature import (
    Attributes,
    Classification,
    CreatureCard,
    CreatureImages,
    Identity,
    Presentation,
    Source,
)
from app.services.artist_loader import ArtistConfig, get_artist_registry
from app.services.prompt_builder import (
    NEGATIVE_PROMPT,
    RARITY_DIRECTIVES,
    build_card_prompt,
    build_headshot_color_prompt,
    build_headshot_pencil_prompt,
    derive_build,
    derive_distinctive_features,
    derive_expression,
    derive_magical_presence,
)


def _make_creature(**overrides) -> CreatureCard:
    """Create a test creature with defaults."""
    defaults = {
        "identity": Identity(
            creature_id="WF-v1-RARE-FOREST-ELF-8A4C91B2",
            creature_signature="RARE|FOREST|ELF|GROVE_ELF|EARTH|MEDIUM|CAUTIOUS|MOSSBOUND",
        ),
        "source": Source(
            canonical_id="EAN_13|5012345678900|WILDERNESS_FRIENDS|v1",
            code_type="EAN_13",
            raw_value="5012345678900",
        ),
        "classification": Classification(
            rarity="RARE",
            biome="FOREST",
            family="NATURE_SPIRIT",
            species="ELF",
            sub_type="GROVE_ELF",
            element="EARTH",
            temperament="CAUTIOUS",
            size="MEDIUM",
            variant="MOSSBOUND",
        ),
        "presentation": Presentation(
            name="Frostborn Ice Dragon",
            title="The Warden of Hollow Pines",
            primary_color="Emerald",
            secondary_color="Amber",
            sigil="leaf",
            frame_style="natural",
        ),
        "attributes": Attributes(
            power=55,
            defense=40,
            agility=70,
            wisdom=65,
            ferocity=30,
            magic=75,
            luck=45,
        ),
    }
    defaults.update(overrides)
    return CreatureCard(**defaults)


def _get_kaelith() -> ArtistConfig:
    registry = get_artist_registry()
    return registry.get("kaelith")


# ── Derivation functions ──────────────────────────────────────────────────


class TestDeriveBuild:
    def test_high_defense(self):
        assert "armored" in derive_build(50, 75)

    def test_high_power(self):
        assert "muscular" in derive_build(80, 50)

    def test_low_both(self):
        assert "slender" in derive_build(20, 20)

    def test_defense_gt_power(self):
        assert "sturdy" in derive_build(40, 50)

    def test_balanced(self):
        assert "athletic" in derive_build(50, 40)


class TestDeriveExpression:
    def test_noble_low_ferocity(self):
        result = derive_expression("NOBLE", 30)
        assert "regal" in result
        assert "bared teeth" not in result

    def test_fierce_high_ferocity(self):
        result = derive_expression("FIERCE", 80)
        assert "battle-ready" in result
        assert "bared teeth" in result

    def test_medium_ferocity(self):
        result = derive_expression("PLAYFUL", 55)
        assert "mischievous" in result
        assert "fierce glint" in result

    def test_unknown_temperament(self):
        result = derive_expression("UNKNOWN", 30)
        assert result == "neutral"


class TestDeriveMagicalPresence:
    def test_very_high(self):
        assert "arcane sigils" in derive_magical_presence(85)

    def test_high(self):
        assert "crackling" in derive_magical_presence(65)

    def test_medium(self):
        assert "shimmer" in derive_magical_presence(45)

    def test_low(self):
        assert "faint" in derive_magical_presence(25)

    def test_none(self):
        assert "no visible" in derive_magical_presence(15)


class TestDeriveDistinctiveFeatures:
    def test_high_wisdom_and_luck(self):
        result = derive_distinctive_features(85, 85)
        assert "rune markings" in result
        assert "glowing knowing eyes" in result
        assert "golden ornamental" in result
        assert "radiant halo" in result

    def test_low_both(self):
        result = derive_distinctive_features(30, 30)
        assert "natural, unadorned" in result

    def test_medium_wisdom_only(self):
        result = derive_distinctive_features(65, 30)
        assert "rune markings" in result
        assert "golden" not in result


# ── Prompt builders ──────────────────────────────────────────────────────


class TestBuildCardPrompt:
    def test_contains_creature_details(self):
        creature = _make_creature()
        artist = _get_kaelith()
        prompt = build_card_prompt(creature, artist)

        assert "GROVE_ELF" in prompt
        assert "MEDIUM" in prompt
        assert "MOSSBOUND" in prompt
        assert "FOREST" in prompt
        assert "EARTH" in prompt
        assert "CAUTIOUS" in prompt
        assert "Emerald" in prompt
        assert "Amber" in prompt

    def test_contains_artist_style(self):
        creature = _make_creature()
        artist = _get_kaelith()
        prompt = build_card_prompt(creature, artist)
        assert "Kaelith" in prompt

    def test_contains_rarity_directive(self):
        creature = _make_creature()
        artist = _get_kaelith()
        prompt = build_card_prompt(creature, artist)
        assert "RARE" in prompt
        assert RARITY_DIRECTIVES["RARE"] in prompt

    def test_contains_visual_derivations(self):
        creature = _make_creature()
        artist = _get_kaelith()
        prompt = build_card_prompt(creature, artist)
        # magic=75 should give visible energy
        assert "magical" in prompt.lower() or "energy" in prompt.lower()

    def test_no_text_instruction(self):
        creature = _make_creature()
        artist = _get_kaelith()
        prompt = build_card_prompt(creature, artist)
        assert "Do not include any text" in prompt


class TestBuildHeadshotColorPrompt:
    def test_contains_creature_type(self):
        creature = _make_creature()
        artist = _get_kaelith()
        prompt = build_headshot_color_prompt(creature, artist)
        assert "GROVE_ELF" in prompt
        assert "ELF" in prompt

    def test_contains_reference_instruction(self):
        creature = _make_creature()
        artist = _get_kaelith()
        prompt = build_headshot_color_prompt(creature, artist)
        assert "Same character as the reference" in prompt

    def test_contains_artist_style(self):
        creature = _make_creature()
        artist = _get_kaelith()
        prompt = build_headshot_color_prompt(creature, artist)
        assert "Kaelith" in prompt


class TestBuildHeadshotPencilPrompt:
    def test_pencil_style(self):
        creature = _make_creature()
        prompt = build_headshot_pencil_prompt(creature)
        assert "pencil sketch" in prompt.lower()
        assert "Black and white" in prompt

    def test_no_color(self):
        creature = _make_creature()
        prompt = build_headshot_pencil_prompt(creature)
        assert "No color" in prompt

    def test_no_artist_style(self):
        creature = _make_creature()
        prompt = build_headshot_pencil_prompt(creature)
        assert "Kaelith" not in prompt


class TestNegativePrompt:
    def test_negative_prompt_has_key_exclusions(self):
        assert "text" in NEGATIVE_PROMPT
        assert "watermark" in NEGATIVE_PROMPT
        assert "border" in NEGATIVE_PROMPT
        assert "blurry" in NEGATIVE_PROMPT
