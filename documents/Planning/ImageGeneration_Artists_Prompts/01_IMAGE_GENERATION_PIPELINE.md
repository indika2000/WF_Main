# Image Generation Pipeline — Architecture & Design

## Overview

This document defines the end-to-end pipeline for generating unique character artwork when a user scans a barcode. The system produces three image types per creature, uses an artist persona system for stylistic variety, and handles concurrency via a background job queue with SSE-based real-time updates to the mobile client.

**Primary Image LLM:** Google Gemini Imagen 3 (`imagen-3.0-generate-002`)

---

## 1. Pipeline Flow

```
User scans barcode
       │
       ▼
┌──────────────────┐
│ Character Service │──── Creature generated (deterministic, <1s)
│ POST /generate    │
└──────┬───────────┘
       │
       ▼
  Does creature already have images?
       │
  YES ─┤──▶ Return creature + cached image URLs immediately
       │
  NO ──┤──▶ Create image generation jobs (3 jobs)
       │    ├── Priority 1: Card image (immediate)
       │    ├── Priority 2: Headshot color (after card completes)
       │    └── Priority 3: Headshot pencil (after card completes)
       │
       ▼
  Return creature data to mobile (no images yet)
  Mobile shows reveal screen with placeholder + "painting" animation
       │
       ▼
┌──────────────────┐     ┌──────────────┐     ┌──────────────┐
│  Background      │────▶│  LLM Service │────▶│ Image Service│
│  Image Worker    │     │  (Gemini)    │     │  (storage)   │
│  (in char-svc)   │     └──────────────┘     └──────────────┘
└──────┬───────────┘
       │
       ▼
  Card image ready ──▶ SSE push to mobile ──▶ Reveal screen updates live
  Headshots queued  ──▶ Process in background ──▶ Available in collection later
```

---

## 2. Image Types Per Creature

| Type | Purpose | Priority | Size | When Available |
|------|---------|----------|------|----------------|
| **Card** | Main collectible card artwork | 1 (immediate) | Portrait (see §3) | During reveal screen |
| **Headshot Color** | Profile avatar, full color bust | 2 (background) | Square 1:1 | After card completes |
| **Headshot Pencil** | Pencil outline sketch for profile/trading | 3 (background) | Square 1:1 | After card completes |

**Sequencing:** Card image must complete first. Headshot jobs use the card image as a visual reference to ensure the headshots depict the same character with consistent features, proportions, and markings.

---

## 3. Gemini Imagen 3 — API Configuration

**Model:** `imagen-3.0-generate-002`

### Aspect Ratio Support

Imagen 3 supports the `aspect_ratio` parameter with these values:
- `1:1` (square — default)
- `3:4` (portrait)
- `4:3` (landscape)
- `9:16` (tall portrait)
- `16:9` (wide landscape)

**Our usage:**
- Card image: `3:4` portrait (matches card layout, gives full-body framing)
- Headshot color: `1:1` square (profile avatar)
- Headshot pencil: `1:1` square (profile avatar)

### Style Reference Support

Style-guided generation uses a **different model and method** than standard generation:

| Method | Model | Use Case |
|--------|-------|----------|
| `generate_images()` | `imagen-3.0-generate-002` | Standard text-to-image (no style refs) |
| `edit_image()` | `imagen-3.0-capability-001` | Style-referenced generation |

**Style reference details:**
- Uses `types.StyleReferenceImage` with `types.StyleReferenceConfig`
- Reference images influence **style only** (brushwork, palette tendencies, rendering technique)
- Reference images do NOT influence content/subject matter
- Up to 4 reference images per request
- Requires the `edit_image()` API path, not `generate_images()`

**Implementation approach — two modes:**

1. **With style references (preferred):** Use `edit_image()` + `imagen-3.0-capability-001` + `StyleReferenceImage` list. Artist reference images are loaded from image service storage at worker startup and cached in memory as bytes.

2. **Without style references (fallback):** Use `generate_images()` + `imagen-3.0-generate-002` with the artist's style directive baked entirely into the text prompt. Used when reference images aren't configured or the style reference API fails.

```python
# Mode 1: Style-referenced generation
from google.genai import types

style_refs = [
    types.StyleReferenceImage(
        reference_image=types.Image(image_bytes=ref_bytes),
        config=types.StyleReferenceConfig(style_description=artist.style_directive),
    )
    for ref_bytes in artist.reference_image_bytes
]

result = await client.aio.models.edit_image(
    model="imagen-3.0-capability-001",
    prompt=prompt,
    reference_images=style_refs,
    config=types.EditImageConfig(
        edit_mode="STYLE_REFERENCE",
        number_of_images=1,
        output_mime_type="image/png",
    ),
)

# Mode 2: Standard generation (fallback — no style refs)
result = await client.aio.models.generate_images(
    model="imagen-3.0-generate-002",
    prompt=prompt,  # includes artist style directive in text
    config=types.GenerateImagesConfig(
        number_of_images=1,
        aspect_ratio="3:4",
        safety_filter_level="BLOCK_ONLY_HIGH",
        person_generation="DONT_ALLOW",
        output_mime_type="image/png",
    ),
)
```

> **Note:** The `edit_image()` method may not support `aspect_ratio` directly.
> If not, we generate at default ratio and crop/resize in the image service.
> This needs to be verified during implementation.

### Key Parameters

```python
# Standard generation config
generation_config = types.GenerateImagesConfig(
    number_of_images=1,
    aspect_ratio="3:4",                    # Portrait for card art
    safety_filter_level="BLOCK_ONLY_HIGH",
    person_generation="DONT_ALLOW",        # Fantasy creatures only
    output_mime_type="image/png",
)
```

### Additional Parameters Available

| Parameter | Values | Notes |
|-----------|--------|-------|
| `number_of_images` | 1-4 | We use 1 |
| `aspect_ratio` | `1:1`, `3:4`, `4:3`, `9:16`, `16:9` | Card=`3:4`, headshots=`1:1` |
| `safety_filter_level` | `BLOCK_LOW_AND_ABOVE`, `BLOCK_MEDIUM_AND_ABOVE`, `BLOCK_ONLY_HIGH` | Most permissive for fantasy art |
| `person_generation` | `DONT_ALLOW`, `ALLOW_ADULT` | Block human faces |
| `output_mime_type` | `image/png`, `image/jpeg` | PNG for quality |
| `add_watermark` | boolean | SynthID watermark — disable for card art |
| `negative_prompt` | string | Exclude unwanted elements from output |

### Negative Prompt (applied to all image types)

```python
NEGATIVE_PROMPT = (
    "text, words, letters, numbers, watermark, signature, border, frame, "
    "card border, UI elements, logo, title, label, speech bubble, "
    "blurry, low quality, distorted, deformed"
)
```

### Provider Configuration Update

```yaml
# providers.yml addition for character art
character_art:
  provider: gemini
  models:
    generate: imagen-3.0-generate-002      # Standard text-to-image
    style_ref: imagen-3.0-capability-001   # Style-referenced generation
  timeout: 90
  default_aspect_ratio: "3:4"
  number_of_images: 1
  safety_filter_level: BLOCK_ONLY_HIGH
  person_generation: DONT_ALLOW
  output_mime_type: "image/png"
```

---

## 4. Prompt Architecture

### Three-Layer Composition

Every image prompt is composed from three layers:

```
┌─────────────────────────────────────┐
│ ARTIST STYLE LAYER                  │  ← From artist persona config
│ Art style, rendering technique,     │
│ visual signature                    │
├─────────────────────────────────────┤
│ SUBJECT LAYER                       │  ← From creature classification
│ Species, biome, element, colors,    │
│ temperament, size, variant          │
├─────────────────────────────────────┤
│ SEED LAYER                          │  ← From creature attributes (stats)
│ Visual weight modifiers that make   │
│ same-archetype creatures look       │
│ different                           │
└─────────────────────────────────────┘
```

### Prompt Template — Card Image

```
Create a collectible fantasy trading card illustration of a {SIZE} {VARIANT} {SUB_TYPE}.

This {SPECIES} dwells in the {BIOME} and channels {ELEMENT} energy.
Its temperament is {TEMPERAMENT}.

Visual characteristics:
- Dominant colors: {PRIMARY_COLOR} and {SECONDARY_COLOR}
- Build: {DERIVED_FROM_POWER_DEFENSE}
- Expression: {DERIVED_FROM_TEMPERAMENT_FEROCITY}
- Magical presence: {DERIVED_FROM_MAGIC_STAT}
- Distinctive features: {DERIVED_FROM_LUCK_WISDOM}

Rarity: {RARITY} — {COMPLEXITY_DIRECTIVE}

{ARTIST_STYLE_DIRECTIVE}

Full body portrait, centered composition, contextual {BIOME} background.
Do not include any text, borders, frames, or card elements — character only.
```

### Stat-to-Visual Mapping (Seed Layer)

Stats drive visual differentiation between creatures that share the same archetype:

| Attribute | Low (10-30) | Medium (30-60) | High (60-100) |
|-----------|-------------|-----------------|----------------|
| **Power** | Slender, delicate frame | Athletic build | Muscular, imposing, large horns/claws |
| **Defense** | Exposed skin/fur, minimal armor | Partial natural armor | Thick scales/bark/plate, heavy shell |
| **Agility** | Sturdy, grounded stance | Balanced pose | Lean/lithe, dynamic pose, wind-swept |
| **Wisdom** | Youthful, bright-eyed | Alert, observant features | Glowing eyes, ancient markings, runes |
| **Ferocity** | Gentle, soft expression | Neutral, watchful | Bared teeth, battle scars, aggressive stance |
| **Magic** | No magical effects | Subtle shimmer | Arcane sigils, floating particles, ethereal glow |
| **Luck** | Plain features | Minor ornamental detail | Golden shimmer, lucky charms, radiant halo |

**Derivation functions:**

```python
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
```

### Rarity Complexity Directives

```python
RARITY_DIRECTIVES = {
    "COMMON": "clean, simple design with minimal detail",
    "UNCOMMON": "moderate detail with one distinctive feature",
    "RARE": "detailed illustration with multiple visual elements and rich textures",
    "EPIC": "highly detailed with layered visual effects, dynamic lighting, and intricate patterns",
    "LEGENDARY": "extraordinarily detailed, multiple visual layers, luminous magical effects, "
                  "cinematic quality, every surface has rich texture and detail",
}
```

### Prompt Template — Headshot Color

Uses `edit_image()` with the card image as a `SubjectReferenceImage` to maintain character consistency:

```python
# The card image is passed as a subject reference
subject_ref = types.SubjectReferenceImage(
    reference_image=types.Image(image_bytes=card_image_bytes),
    config=types.SubjectReferenceConfig(subject_type="SUBJECT_TYPE_DEFAULT"),
)
```

```
Portrait headshot of a {VARIANT} {SUB_TYPE}, a {SPECIES} creature.
Bust framing showing head and upper body only.
Same character as the reference — maintain exact features, markings, and coloring.
Dominant colors: {PRIMARY_COLOR} and {SECONDARY_COLOR}.
{ARTIST_STYLE_DIRECTIVE}
Clean background, portrait orientation.
Do not include any text or decorative elements.
```

### Prompt Template — Headshot Pencil

Also uses the card image as subject reference, with explicit pencil style override:

```
Detailed pencil sketch of a {VARIANT} {SUB_TYPE}, a {SPECIES} creature.
Bust framing showing head and upper body only.
Same character as the reference — maintain exact features, markings, and proportions.
Black and white pencil drawing, clean line art with cross-hatching for shading.
No color, no background, white paper.
Do not include any text or decorative elements.
```

> **Note on headshot generation:** Both headshot types use `edit_image()` with
> `imagen-3.0-capability-001`. The card image serves as a `SubjectReferenceImage`
> (maintaining character identity), while the style reference images may be
> omitted for the pencil variant (pure line art style is better described in text).
> Aspect ratio for headshots: `1:1` (square).

---

## 5. Artist Persona System

### Overview

Four artist personas provide stylistic variety across the creature catalog. Each artist has:
- A name and background story (for UX — displayed during generation)
- A detailed art style description (injected into the LLM prompt)
- 3-5 reference images (passed to Imagen 3 as style references)
- Biome and family affinities (rule-based assignment)

### Artist Profiles

#### Kaelith — "The Verdant Illustrator"

**Style:** Soft watercolor washes with luminous highlights. Dappled sunlight filtering through leaves. Organic, flowing lines. Dreamy, ethereal atmosphere with visible brushstrokes. Muted earth tones punctuated by bright natural accents.

**Style Directive:**
```
Art style by Kaelith: Soft watercolor rendering with luminous highlights and dappled light.
Organic flowing lines, visible brushstrokes, dreamy ethereal atmosphere.
Muted earth tones with bright natural accents. Painterly and warm.
```

**Biome Affinities:**
```
FOREST, DEEP_FOREST, ENCHANTED_FOREST, ANCIENT_FOREST, BAMBOO_FOREST,
MUSHROOM_GROVE, GRASSLAND, SAVANNA, RIVER, LAKE, WATERFALL, JUNGLE,
RAINFOREST, CANOPY
```

**Family Affinities:**
```
NATURE_SPIRIT, SMALL_CREATURE, BIRD
```

#### Thornforge — "The Iron Chronicler"

**Style:** Heavy ink linework with rich digital coloring. Strong contrast, dramatic shadows, and textured surfaces. Gritty, detailed, almost tactile quality. Dark atmospheric backgrounds with sharp highlights. Industrial precision meets fantasy.

**Style Directive:**
```
Art style by Thornforge: Heavy ink linework with rich saturated colors and dramatic shadows.
Strong contrast, textured surfaces with almost tactile quality.
Gritty and detailed with dark atmospheric tones and sharp highlights.
Bold and impactful with industrial precision.
```

**Biome Affinities:**
```
VOLCANIC_MOUNTAIN, LAVA_FIELD, RUINS, CEMETERY, BADLANDS, MOUNTAIN,
HIGH_PEAK, DESERT, SAND_DUNE, CAVE, UNDERGROUND, STEPPE
```

**Family Affinities:**
```
DRAGON, BEAST, UNDEAD, CONSTRUCT
```

#### Solara — "The Prism Weaver"

**Style:** Vibrant cel-shaded illustration with bold, clean color planes. Strong silhouettes and confident outlines. Anime-adjacent but with Western fantasy proportions. Bright, optimistic palette with dynamic compositions. Clean and modern.

**Style Directive:**
```
Art style by Solara: Vibrant cel-shaded illustration with bold clean color planes.
Strong silhouettes, confident outlines, bright optimistic palette.
Dynamic composition with clean modern rendering.
Stylized proportions, sharp color transitions, minimal texture.
```

**Biome Affinities:**
```
SKY_REALM, CLOUD_PEAKS, ISLAND, COAST, CLIFF, OASIS, CORAL_REEF
```

**Family Affinities:**
```
HUMANOID, MYTHIC, INSECTOID
```

#### Mistweaver — "The Depth Painter"

**Style:** Atmospheric realism with moody, cinematic lighting. Volumetric fog, subsurface scattering, and chiaroscuro. Deep, rich color palette dominated by blues, teals, and purples. Mysterious and immersive. Environmental storytelling through light and shadow.

**Style Directive:**
```
Art style by Mistweaver: Atmospheric realism with moody cinematic lighting.
Volumetric fog, subsurface scattering, deep rich color palette.
Dominated by blues, teals, and purples with chiaroscuro lighting.
Mysterious and immersive with environmental depth.
```

**Biome Affinities:**
```
OCEAN, DEEP_OCEAN, SWAMP, MANGROVE_SWAMP, BOG, CAVE, CRYSTAL_CAVE,
GLACIER, FROZEN_TUNDRA, ICE_CAVE, SNOWLAND, VOID
```

**Family Affinities:**
```
AQUATIC, REPTILE
```

### Artist Assignment Algorithm

Rule-based with deterministic tiebreaker:

```python
def assign_artist(creature: CreatureCard) -> str:
    """Assign an artist to a creature based on biome and family affinities.

    Priority:
    1. Check biome affinity first (biome is more visually impactful)
    2. Check family affinity as secondary
    3. If multiple artists match, use hash byte for deterministic tiebreak
    4. If no match, use hash byte to pick any artist
    """
    biome = creature.classification.biome
    family = creature.classification.family

    candidates = []

    # Check biome affinities
    for artist_id, config in ARTISTS.items():
        if biome in config["biome_affinities"]:
            candidates.append(artist_id)

    # If no biome match, check family
    if not candidates:
        for artist_id, config in ARTISTS.items():
            if family in config["family_affinities"]:
                candidates.append(artist_id)

    # If still no match, all artists are candidates
    if not candidates:
        candidates = list(ARTISTS.keys())

    # Deterministic selection from candidates using creature hash
    # Use byte[2] (currently unused in generation) as tiebreaker
    hash_bytes = hashlib.sha256(
        creature.source.canonical_id.encode()
    ).digest()
    index = hash_bytes[2] % len(candidates)
    return candidates[index]
```

### Artist Configuration Storage

**Config file:** `services/character-service/config/artists.yml`

```yaml
artists:
  kaelith:
    name: "Kaelith"
    title: "The Verdant Illustrator"
    style_directive: |
      Art style by Kaelith: Soft watercolor rendering with luminous highlights
      and dappled light. Organic flowing lines, visible brushstrokes, dreamy
      ethereal atmosphere. Muted earth tones with bright natural accents.
      Painterly and warm.
    biome_affinities:
      - FOREST
      - DEEP_FOREST
      - ENCHANTED_FOREST
      - ANCIENT_FOREST
      - BAMBOO_FOREST
      - MUSHROOM_GROVE
      - GRASSLAND
      - SAVANNA
      - RIVER
      - LAKE
      - WATERFALL
      - JUNGLE
      - RAINFOREST
      - CANOPY
    family_affinities:
      - NATURE_SPIRIT
      - SMALL_CREATURE
      - BIRD
    reference_images: []  # Populated after uploading to image service

  thornforge:
    name: "Thornforge"
    title: "The Iron Chronicler"
    style_directive: |
      Art style by Thornforge: Heavy ink linework with rich saturated colors
      and dramatic shadows. Strong contrast, textured surfaces with almost
      tactile quality. Gritty and detailed with dark atmospheric tones and
      sharp highlights. Bold and impactful with industrial precision.
    biome_affinities:
      - VOLCANIC_MOUNTAIN
      - LAVA_FIELD
      - RUINS
      - CEMETERY
      - BADLANDS
      - MOUNTAIN
      - HIGH_PEAK
      - DESERT
      - SAND_DUNE
      - CAVE
      - UNDERGROUND
      - STEPPE
    family_affinities:
      - DRAGON
      - BEAST
      - UNDEAD
      - CONSTRUCT
    reference_images: []

  solara:
    name: "Solara"
    title: "The Prism Weaver"
    style_directive: |
      Art style by Solara: Vibrant cel-shaded illustration with bold clean
      color planes. Strong silhouettes, confident outlines, bright optimistic
      palette. Dynamic composition with clean modern rendering. Stylized
      proportions, sharp color transitions, minimal texture.
    biome_affinities:
      - SKY_REALM
      - CLOUD_PEAKS
      - ISLAND
      - COAST
      - CLIFF
      - OASIS
      - CORAL_REEF
    family_affinities:
      - HUMANOID
      - MYTHIC
      - INSECTOID
    reference_images: []

  mistweaver:
    name: "Mistweaver"
    title: "The Depth Painter"
    style_directive: |
      Art style by Mistweaver: Atmospheric realism with moody cinematic
      lighting. Volumetric fog, subsurface scattering, deep rich color palette.
      Dominated by blues, teals, and purples with chiaroscuro lighting.
      Mysterious and immersive with environmental depth.
    biome_affinities:
      - OCEAN
      - DEEP_OCEAN
      - SWAMP
      - MANGROVE_SWAMP
      - BOG
      - CAVE
      - CRYSTAL_CAVE
      - GLACIER
      - FROZEN_TUNDRA
      - ICE_CAVE
      - SNOWLAND
      - VOID
    family_affinities:
      - AQUATIC
      - REPTILE
    reference_images: []
```

**Reference images:** Stored in the image service under `_system/artists/{artist_id}/references/`. Image IDs added to the `reference_images` list in the YAML after initial upload. These are loaded at service startup and cached in memory.

---

## 6. Job Queue System

### Overview

Image generation jobs are stored in MongoDB (`image_generation_jobs` collection) and processed by a background async worker running within the character service process.

### Job Schema

```python
{
    "job_id": "uuid",
    "creature_id": "WF-v1-RARE-FOREST-ELF-8A4C91B2",
    "image_type": "card",               # "card" | "headshot_color" | "headshot_pencil"
    "status": "pending",                 # pending | processing | completed | failed
    "priority": 1,                       # 1=card, 2=headshot_color, 3=headshot_pencil
    "artist_id": "kaelith",
    "prompt": "...",                      # Full composed prompt
    "reference_image_id": null,          # For headshots: the completed card image_id
    "result_image_id": null,             # Set on completion
    "attempts": 0,
    "max_attempts": 3,
    "error": null,
    "created_at": datetime,
    "started_at": null,
    "completed_at": null,
    "requested_by": "user_id",
}
```

### Job Lifecycle

```
pending ──▶ processing ──▶ completed
                │
                ▼
             failed (retry if attempts < max_attempts)
                │
                ▼
             pending (re-queued with incremented attempt count)
```

### Worker Architecture

**Background async task** in the character service process (not a separate service):

```python
async def image_worker_loop():
    """Background worker that processes image generation jobs.

    Runs as an asyncio task started during service lifespan.
    Concurrency limit: MAX_CONCURRENT_JOBS (configurable, default 2).
    """
    while True:
        # Atomically claim next pending job (priority ASC, created_at ASC)
        job = await db.image_generation_jobs.find_one_and_update(
            {
                "status": "pending",
                # Headshot jobs only run when card is done
                "$or": [
                    {"image_type": "card"},
                    {"image_type": {"$ne": "card"}, "reference_image_id": {"$ne": None}},
                ],
            },
            {
                "$set": {"status": "processing", "started_at": datetime.utcnow()},
                "$inc": {"attempts": 1},
            },
            sort=[("priority", 1), ("created_at", 1)],
            return_document=True,
        )

        if not job:
            await asyncio.sleep(2)  # No work, poll again
            continue

        try:
            image_id = await generate_and_store_image(job)

            # Mark completed
            await db.image_generation_jobs.update_one(
                {"job_id": job["job_id"]},
                {"$set": {
                    "status": "completed",
                    "result_image_id": image_id,
                    "completed_at": datetime.utcnow(),
                }},
            )

            # Update creature's image references
            image_field = f"images.{job['image_type']}"
            await db.creatures.update_one(
                {"identity.creature_id": job["creature_id"]},
                {"$set": {image_field: image_id}},
            )

            # If card just completed, unlock headshot jobs
            if job["image_type"] == "card":
                await db.image_generation_jobs.update_many(
                    {
                        "creature_id": job["creature_id"],
                        "image_type": {"$in": ["headshot_color", "headshot_pencil"]},
                    },
                    {"$set": {"reference_image_id": image_id}},
                )

            # Push SSE event
            await notify_image_ready(job["creature_id"], job["image_type"], image_id)

        except Exception as e:
            if job["attempts"] >= job["max_attempts"]:
                await db.image_generation_jobs.update_one(
                    {"job_id": job["job_id"]},
                    {"$set": {"status": "failed", "error": str(e)}},
                )
            else:
                # Re-queue for retry
                await db.image_generation_jobs.update_one(
                    {"job_id": job["job_id"]},
                    {"$set": {"status": "pending", "error": str(e)}},
                )
```

### Concurrency Control

- `MAX_CONCURRENT_JOBS = 2` (configurable via env var)
- Worker runs as asyncio semaphore-guarded tasks
- Multiple jobs can process in parallel up to the limit
- Prevents overwhelming the Gemini API with too many concurrent requests

### Duplicate Prevention

Before creating jobs, check if the creature already has images:

```python
async def ensure_image_jobs(creature_id: str, creature: CreatureCard, user_id: str):
    """Create image generation jobs if they don't already exist."""
    existing_jobs = await db.image_generation_jobs.count_documents(
        {"creature_id": creature_id, "status": {"$ne": "failed"}}
    )
    if existing_jobs > 0:
        return  # Jobs already exist (pending/processing/completed)

    creature_doc = await db.creatures.find_one(
        {"identity.creature_id": creature_id}
    )
    if creature_doc and creature_doc.get("images", {}).get("card"):
        return  # Card image already exists

    # Create the 3 jobs
    artist_id = assign_artist(creature)
    card_prompt = build_card_prompt(creature, artist_id)

    jobs = [
        {
            "job_id": str(uuid4()),
            "creature_id": creature_id,
            "image_type": "card",
            "status": "pending",
            "priority": 1,
            "artist_id": artist_id,
            "prompt": card_prompt,
            "reference_image_id": None,
            "result_image_id": None,
            "attempts": 0,
            "max_attempts": 3,
            "error": None,
            "created_at": datetime.utcnow(),
            "started_at": None,
            "completed_at": None,
            "requested_by": user_id,
        },
        # headshot_color and headshot_pencil — similar but priority 2,3
        # reference_image_id is None until card completes
    ]
    await db.image_generation_jobs.insert_many(jobs)
```

---

## 7. SSE (Server-Sent Events) for Real-Time Updates

### Endpoint

```
GET /api/characters/{creature_id}/images/stream
```

### Flow

1. Mobile subscribes to SSE endpoint after creature generation
2. Character service holds the connection open
3. When image worker completes a job, it pushes an event
4. Mobile receives event and updates UI in real-time

### Event Format

```
event: image_ready
data: {"creature_id": "WF-v1-...", "image_type": "card", "image_url": "/api/images/..."}

event: image_ready
data: {"creature_id": "WF-v1-...", "image_type": "headshot_color", "image_url": "/api/images/..."}

event: image_failed
data: {"creature_id": "WF-v1-...", "image_type": "card", "error": "Generation failed"}

event: keepalive
data: {}
```

### Mobile Implementation

```typescript
// In character reveal screen
useEffect(() => {
  if (!creatureId || cardImageUrl) return;

  const eventSource = new EventSource(
    `${API_URL}/api/characters/${creatureId}/images/stream`
  );

  eventSource.addEventListener("image_ready", (event) => {
    const data = JSON.parse(event.data);
    if (data.image_type === "card") {
      setCardImageUrl(data.image_url);
    }
  });

  return () => eventSource.close();
}, [creatureId, cardImageUrl]);
```

### Fallback: Polling

If SSE is not feasible (e.g., gateway proxy issues), fall back to polling:

```
GET /api/characters/{creature_id}/images
→ { card: { status, image_url }, headshot_color: { status }, headshot_pencil: { status } }
```

Poll every 2-3 seconds until card image is ready.

---

## 8. Image Storage & Caching

### Storage Path Structure

```
/storage/
  creatures/
    {season}/
      {creature_id}/
        card.png                  # Main card art (3:4 portrait)
        card_thumbnail.webp       # 256px thumbnail for collection grid
        card_medium.webp          # 512px for collection detail
        headshot_color.png        # Color headshot (1:1 square)
        headshot_color_thumb.webp # 128px thumbnail
        headshot_pencil.png       # Pencil outline (1:1 square)
        headshot_pencil_thumb.webp
  _system/
    artists/
      kaelith/
        reference_01.png
        reference_02.png
        reference_03.png
      thornforge/
        reference_01.png
        ...
```

### Cache Strategy

- **creature_id** is deterministic (same barcode → same creature_id always)
- Before generating, check: `creature.images.card` is not null → skip generation
- Same barcode rescanned → same creature → cached images returned immediately
- **No LLM call is ever made twice for the same creature_id**
- Claimed variants have their own creature_id → get their own unique artwork

### Creature Document Update

```python
# Before (current)
{
    "image_id": null,  # Single image reference
}

# After (updated)
{
    "images": {
        "card": "uuid-or-null",
        "headshot_color": "uuid-or-null",
        "headshot_pencil": "uuid-or-null",
    },
}
```

---

## 9. UX During Image Generation

### Reveal Screen States

```
State 1: CREATURE_REVEALED (immediate)
  ├── Creature name, stats, rarity — all shown
  ├── Image area: Stylized silhouette with shimmer/pulse animation
  ├── Artist attribution: "Kaelith is painting your creature..."
  └── Subtle animated brushstroke effect over placeholder

State 2: IMAGE_ARRIVED (5-15s later, via SSE)
  ├── Crossfade from placeholder to real card image
  ├── Brief "painting complete" flourish animation
  └── "Add to Collection" button now shows real art

State 3: IMAGE_FAILED (error case)
  ├── Show creature with placeholder art
  ├── "Art will be available soon" message
  └── Background retry — image appears in collection later
```

### Collection Screen

- Grid cards initially show placeholder art if image hasn't generated yet
- Once image exists, collection card shows the card_thumbnail
- No loading spinner — graceful fallback to placeholder
- Images appear automatically on next screen visit after generation completes

---

## 10. Database Indexes

```python
# New indexes for image generation
await db.image_generation_jobs.create_index("job_id", unique=True)
await db.image_generation_jobs.create_index(
    [("status", 1), ("priority", 1), ("created_at", 1)]
)
await db.image_generation_jobs.create_index("creature_id")
```

---

## 11. Service Integration Points

### Character Service → LLM Service

```
POST /generate/image
{
    "prompt": "...",
    "provider": "gemini",
    "config": {
        "model": "imagen-3.0-generate-002",
        "aspect_ratio": "3:4",
        "number_of_images": 1,
    },
    "style_references": ["base64-encoded-reference-image-1", ...],
}
```

### Character Service → Image Service

```
POST /images/upload
Content-Type: multipart/form-data

file: <generated-image-bytes>
user_id: "_system"
category: "creature_art"
metadata: {"creature_id": "...", "image_type": "card", "artist_id": "kaelith"}
tags: ["creature", "card", "rare", "forest"]
```

### Gateway Routing

```javascript
// New SSE route in gateway
characterImages: {
    url: 'http://character-service:5002',
    pathPrefix: '/characters',
    // SSE: ensure proxy doesn't buffer/timeout
    timeout: 120000,
}
```

---

## 12. Configuration Summary

| Config | Location | Purpose |
|--------|----------|---------|
| `artists.yml` | `character-service/config/` | Artist personas, style directives, affinities |
| `generation_v1.yml` | `character-service/config/` | Creature enums (existing, no changes) |
| `providers.yml` | `llm-service/config/` | Gemini model config + aspect ratio defaults |
| `config.py` | `character-service/app/` | New settings: `max_concurrent_image_jobs`, `image_service_url` |

---

## 13. Build Order

1. **Artist config** — Create `artists.yml`, add config loader
2. **Prompt builder** — `services/character-service/app/services/prompt_builder.py`
3. **Job queue** — MongoDB collection, indexes, job CRUD
4. **Image worker** — Background async task in character service lifespan
5. **SSE endpoint** — `GET /characters/{creature_id}/images/stream`
6. **Generate endpoint update** — Trigger image jobs after creature creation
7. **Creature model update** — `image_id` → `images` dict
8. **LLM service update** — Accept aspect_ratio + style_references in image generation
9. **Gateway update** — SSE-compatible proxy config
10. **Mobile update** — SSE subscription in reveal screen, image loading in collection
11. **Reference image upload** — Admin/dev script to upload artist reference images
12. **Tests** — Prompt builder unit tests, job queue tests, integration tests
