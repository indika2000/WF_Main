"""Build image generation prompts from creature data and artist personas."""

from app.models.creature import CreatureCard
from app.services.artist_loader import ArtistConfig

# Negative prompt applied to all image types
NEGATIVE_PROMPT = (
    "text, words, letters, numbers, watermark, signature, border, frame, "
    "card border, UI elements, logo, title, label, speech bubble, "
    "blurry, low quality, distorted, deformed"
)

RARITY_DIRECTIVES = {
    "COMMON": "clean, simple design with minimal detail",
    "UNCOMMON": "moderate detail with one distinctive feature",
    "RARE": "detailed illustration with multiple visual elements and rich textures",
    "EPIC": (
        "highly detailed with layered visual effects, dynamic lighting, "
        "and intricate patterns but keeping to the artist's style"
    ),
    "LEGENDARY": (
        "extraordinarily detailed, multiple visual layers, luminous magical effects, "
        "cinematic quality, every surface has rich texture and detail but keeping to the artist's style"
    ),
}


# ---------------------------------------------------------------------------
# Stat-to-visual derivation functions
# ---------------------------------------------------------------------------


def derive_build(power: int, defense: int) -> str:
    """Derive build description from power and defense stats."""
    if defense > 70:
        return "heavily armored with thick natural plating"
    elif power > 70:
        return "powerfully muscular with imposing presence"
    elif power < 30 and defense < 30:
        return "slender and delicate"
    elif defense > power:
        return "sturdy and well-protected"
    else:
        return "athletic and balanced"


def derive_expression(temperament: str, ferocity: int) -> str:
    """Derive expression from temperament and ferocity stat."""
    base = {
        "NOBLE": "regal and composed",
        "CAUTIOUS": "alert and watchful",
        "WILD": "untamed and free-spirited",
        "FIERCE": "intense and battle-ready",
        "PLAYFUL": "mischievous and bright-eyed",
        "CURIOUS": "wide-eyed and inquisitive",
        "AGGRESSIVE": "menacing and hostile",
        "MYSTICAL": "serene and otherworldly",
    }.get(temperament, "neutral")

    if ferocity > 70:
        return f"{base}, with bared teeth and battle scars"
    elif ferocity > 50:
        return f"{base}, with a fierce glint in the eyes"
    return base


def derive_magical_presence(magic: int) -> str:
    """Derive magical aura description from magic stat."""
    if magic > 80:
        return "intense magical aura with floating arcane sigils and ethereal particles"
    elif magic > 60:
        return "visible magical energy crackling around the body"
    elif magic > 40:
        return "subtle magical shimmer and faint arcane markings"
    elif magic > 20:
        return "faint mystical glow"
    return "no visible magical effects"


def derive_distinctive_features(wisdom: int, luck: int) -> str:
    """Derive distinctive features from wisdom and luck stats."""
    features = []
    if wisdom > 60:
        features.append("ancient rune markings etched into skin")
    if wisdom > 80:
        features.append("glowing knowing eyes")
    if luck > 60:
        features.append("golden ornamental details")
    if luck > 80:
        features.append("radiant halo-like glow")
    if not features:
        features.append("natural, unadorned appearance")
    return ", ".join(features)


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------


def build_card_prompt(creature: CreatureCard, artist: ArtistConfig) -> str:
    """Build the full prompt for a card image (3:4 portrait, full body)."""
    c = creature.classification
    p = creature.presentation
    a = creature.attributes

    build = derive_build(a.power, a.defense)
    expression = derive_expression(c.temperament, a.ferocity)
    magical = derive_magical_presence(a.magic)
    distinctive = derive_distinctive_features(a.wisdom, a.luck)
    rarity_directive = RARITY_DIRECTIVES.get(c.rarity, RARITY_DIRECTIVES["COMMON"])

    return (
        f"Create an illustration and only an illustration of the following character and it's environment:\n\n "
        f"{c.size} {c.variant} {c.sub_type}.\n\n"
        f"This {c.species} dwells in the {c.biome} and channels {c.element} energy. "
        f"Its temperament is {c.temperament}.\n\n"
        f"with Visual characteristics with should shape the character image:\n"
        f"- Dominant colors: {p.primary_color} and {p.secondary_color}\n"
        f"- Build: {build}\n"
        f"- Expression: {expression}\n"
        f"- Magical presence: {magical}\n"
        f"- Distinctive features: {distinctive}\n\n"
        f"And it's Rarity which should help further define the character uniqueness: {c.rarity} — {rarity_directive}\n\n"
        f"You should use the following artist style directive ensuring that line art is consistent, and keeping to the artist's style: {artist.style_directive}\n\n"
        f"This image should be a Full body portrait, centered composition, contextual {c.biome} background again with the artist's style in mind.\n"
        f"DO NOT include any text, borders, frames, or card elements in the image, this is really important — character and background ONLY."
    )


def build_headshot_color_prompt(creature: CreatureCard, artist: ArtistConfig) -> str:
    """Build prompt for a color headshot (1:1 square, bust framing).

    The card image should be passed as a SubjectReferenceImage separately.
    """
    c = creature.classification
    p = creature.presentation

    return (
        f"Portrait headshot of a {c.variant} {c.sub_type}, "
        f"a {c.species} creature.\n"
        f"Bust framing showing head and upper body only.\n"
        f"Same character as the reference — maintain exact features, "
        f"markings, and coloring.\n"
        f"Dominant colors: {p.primary_color} and {p.secondary_color}.\n"
        f"You should use the following artist style directive ensuring that line art is consistent, and keeping to the artist's style: {artist.style_directive}\n"
        f"Clean background, portrait orientation.\n"
        f"Do not include any text or decorative elements."
    )


def build_headshot_pencil_prompt(creature: CreatureCard) -> str:
    """Build prompt for a pencil sketch headshot (1:1 square, bust framing).

    The card image should be passed as a SubjectReferenceImage separately.
    No artist style directive — pencil style is explicit in the prompt.
    """
    c = creature.classification

    return (
        f"Detailed pencil line art sketch of a {c.variant} {c.sub_type}, "
        f"a {c.species} creature.\n"
        f"Bust framing showing head and upper body only.\n"
        f"Same character as the reference — maintain EXACT features, "
        f"markings, and proportions.\n"
        f"Black and white pencil drawing, clean line art with "
        f"cross-hatching for shading.\n"
        f"No color, no background, the image should only show thehead sketch, and it should look like a rough pencil sketch. On a white background\n"
        f"Do NOT include any text, decorative elements, borders, or any other image artifacts other than the pencil sketch itself."
    )
