# Character Generation System — Deep Architecture Plan

## 1. What This Document Is

This is my (Claude's) deep analysis of your two thinking documents, synthesised into a concrete system plan. It covers: the generation algorithm, where it lives in the architecture, how it handles scale, how it prevents duplication, how it caps supply, how it integrates with the existing services, and how we test it — including a 100s-of-barcodes stress test. I've flagged open questions at the end for discussion before we build.

---

## 2. The Core Idea (Restated Clearly)

A user scans a **real-world barcode** (UPC-A, EAN-13) or a **QR code**. That code is:

1. **Normalised** into a canonical identity string
2. **Hashed** (SHA-256) to produce a deterministic seed
3. **Fed through a generation algorithm** that picks: rarity, biome, species, subtype, element, temperament, size, variant, stats, name, title, visual signals
4. **Checked against a registry** for signature collisions (deterministic reroll if needed)
5. **Checked against supply caps** (e.g., max 10 Legendary Frost Dragons)
6. **Persisted** in a creature registry (MongoDB)
7. Eventually **sent to the LLM/Image Service** for artwork generation, then cached so we never re-generate the same art

Same barcode always produces the same creature. Different users scanning the same barcode get the same creature definition (but each user "owns" their own instance of it).

---

## 3. Where Does This Live? — New Character Service

### Why a Dedicated Service (Not Bolted Onto Existing)

| Option | Pros | Cons |
|--------|------|------|
| **New `character-service`** | Clean separation, owns its own DB collections, no risk of bloating other services, can scale independently | One more container |
| **Inside permissions-service** | Already has user context | Wrong responsibility — permissions is about entitlements, not game logic |
| **Inside commerce-service** | Has user context | Wrong responsibility — commerce is about payments |
| **Inside the gateway** | Already proxies everything | Gateway should stay thin — no business logic |

**Recommendation: New `character-service` (FastAPI, Python 3.12, port 5002)**

This follows the exact same pattern as all existing services: FastAPI + motor + shared utils, Dockerfile with `services/` build context, gateway proxy route at `/api/characters/*`.

### Service Responsibilities

1. **Code normalisation** — validate and normalise UPC-A/EAN-13/QR inputs
2. **Deterministic generation** — SHA-256 seed → algorithm → creature card JSON
3. **Registry management** — store source→creature mappings, creature signatures, supply counters
4. **Supply cap enforcement** — track counts per rarity tier (and per archetype for legendaries)
5. **Collision resolution** — deterministic reroll when signatures collide (per rarity policy)
6. **Art generation orchestration** — call LLM Service for image gen, store result via Image Service, cache the mapping
7. **User collection** — track which users own which creature instances
8. **Generation config** — versioned enums, biome-species maps, rarity weights (stored as YAML/JSON config, not hardcoded)

---

## 4. The Generation Algorithm — Detailed Walkthrough

### 4.1 Input

```json
{
  "code_type": "EAN_13",
  "raw_value": "5012345678900",
  "user_id": "firebase-uid-abc123"
}
```

### 4.2 Normalisation

```
canonical_id = "EAN_13|5012345678900|WILDERNESS_FRIENDS|v1"
```

Rules per code type:
- **UPC_A**: strip whitespace, digits only, exactly 12, preserve leading zeros
- **EAN_13**: strip whitespace, digits only, exactly 13, preserve leading zeros
- **QR**: strip leading/trailing whitespace, preserve exact content

Namespace is `WILDERNESS_FRIENDS` (hardcoded in config). Version `v1` is the generator version — changing it changes the creature a barcode produces (used for future content expansions).

### 4.3 Seed Derivation

```
seed_bytes = SHA-256(canonical_id.encode("utf-8"))  # 32 bytes
```

### 4.4 Byte Allocation

```
byte[0]   → rarity roll (% 100)
byte[1]   → biome (% len(biomes))
byte[2]   → family (derived from species)
byte[3]   → species (% len(eligible_species_for_biome))
byte[4]   → subtype (% len(subtypes_for_species_biome))
byte[5]   → element (% len(elements))
byte[6]   → temperament (% len(temperaments))
byte[7]   → size (% len(sizes))
byte[8]   → variant (% len(variants))
byte[9]   → title role fragment
byte[10]  → primary colour
byte[11]  → secondary colour
byte[12]  → sigil
byte[13]  → frame style
byte[14-20] → stats (power, defense, agility, wisdom, ferocity, magic, luck)
byte[21+] → lore seed, tie-break, future expansion
```

**Critical design rule**: each attribute uses its own dedicated byte(s). Adding new attributes later uses unused bytes (21+) without shifting existing allocations. This means adding "mount type" at byte[22] doesn't change any existing creature.

### 4.5 Rarity Determination

```
rarity_roll = byte[0] % 100

0–69  → COMMON      (70%)
70–89 → UNCOMMON    (20%)
90–96 → RARE        (7%)
97–98 → EPIC        (2%)
99    → LEGENDARY   (1%)
```

**Confirmed (D1)**: All 5 tiers active. Common at 70% gives a strong base for the collection and makes higher tiers feel genuinely special.

### 4.6 Biome-Constrained Species Selection

Species selection is NOT random across all species. It's constrained by biome:

```python
eligible_species = BIOME_SPECIES_MAP[biome]
species = eligible_species[byte[3] % len(eligible_species)]
family = SPECIES_FAMILY_MAP[species]
```

This ensures you never get a Kraken in a Mountain or a Yeti in a Swamp.

### 4.7 Subtype (Biome + Species Variant)

```python
eligible_subtypes = SUBTYPE_MAP[species].get(biome, SUBTYPE_MAP[species]["DEFAULT"])
sub_type = eligible_subtypes[byte[4] % len(eligible_subtypes)]
```

Example: Wolf + Forest → "Wood Wolf" or "Shade Wolf" or "Fern Wolf"
Example: Dragon + Glacier → "Ice Dragon" or "Rime Dragon" or "Glacial Dragon"

### 4.8 Stats (Rarity-Biased)

```python
STAT_RANGES = {
    "COMMON":    {"min": 10, "max": 40},
    "UNCOMMON":  {"min": 25, "max": 55},
    "RARE":      {"min": 40, "max": 70},
    "EPIC":      {"min": 55, "max": 85},
    "LEGENDARY": {"min": 70, "max": 100},
}

range = STAT_RANGES[rarity]
power = range["min"] + (byte[14] % (range["max"] - range["min"] + 1))
# ... same for defense, agility, wisdom, ferocity, magic, luck
```

This prevents weak Legendaries and overpowered Commons.

### 4.9 Name & Title Generation

```
name = f"{variant_display} {subtype_display}"
  → "Mossbound Grove Elf"
  → "Frostborn Ice Dragon"

title = f"The {ROLES[byte[9] % len(ROLES)]} of the {DOMAINS[byte[21] % len(DOMAINS)]}"
  → "The Warden of Hollow Pines"
  → "The Herald of White Storms"
```

### 4.10 Creature Signature

```
signature = f"{rarity}|{biome}|{species}|{sub_type}|{element}|{size}|{temperament}|{variant}"
```

Example: `EPIC|SWAMP|HYDRA|MIRE_HYDRA|POISON|HUGE|AGGRESSIVE|ROTROOT`

This is used for collision detection and supply cap tracking.

---

## 5. Supply Cap System

This is how you limit how many of each type exist. Three layers:

### 5.1 Global Rarity Caps

```json
{
  "SupplyCaps": {
    "COMMON":    null,
    "UNCOMMON":  100000,
    "RARE":      25000,
    "EPIC":      5000,
    "LEGENDARY": 500
  }
}
```

`null` means unlimited. When a rarity cap is hit, the algorithm **downgrades** the rarity to the next available tier.

### 5.2 Per-Archetype Caps (For Top Tiers)

For Legendary and Epic, you may want per-archetype limits:

```json
{
  "ArchetypeCaps": {
    "LEGENDARY": {
      "LEGENDARY|*|DRAGON|*": 10,
      "LEGENDARY|*|PHOENIX|*": 5,
      "LEGENDARY|VOID|*|*": 1
    },
    "EPIC": {
      "EPIC|*|HYDRA|*": 100
    }
  }
}
```

Wildcard matching on the signature. This lets you say "only 10 Legendary Dragons total" or "only 1 Legendary Void creature of any species."

### 5.3 Counter Storage

MongoDB collection: `supply_counters`

```json
{
  "counter_key": "rarity:LEGENDARY",
  "current_count": 342,
  "max_count": 500
}
```

And for archetype caps:
```json
{
  "counter_key": "archetype:LEGENDARY|*|DRAGON|*",
  "current_count": 8,
  "max_count": 10
}
```

**Atomic increment** with `find_one_and_update` + `$inc` to prevent race conditions when 100,000 users generate simultaneously.

### 5.4 What Happens When a Cap Is Hit?

1. Algorithm determines rarity = LEGENDARY
2. Check global cap → LEGENDARY counter at 500/500 → **FULL**
3. **Downgrade**: re-derive as EPIC using `SHA-256(canonical_id + "|downgrade|EPIC")`
4. Check EPIC cap → still has room → proceed
5. The creature is now EPIC, with a `downgraded_from: "LEGENDARY"` field for auditing

This is deterministic — same barcode will always get the same downgrade path.

---

## 6. Collision Handling

### 6.1 Collision Policy Per Rarity

```json
{
  "CollisionPolicy": {
    "COMMON":    "ALLOW",
    "UNCOMMON":  "ALLOW",
    "RARE":      "ALLOW_IF_STATS_DIFFER",
    "EPIC":      "REROLL_ON_SIGNATURE_MATCH",
    "LEGENDARY": "REROLL_ON_ANY_ARCHETYPE_MATCH"
  }
}
```

- **ALLOW**: Multiple creatures can share the exact same signature. Common cards SHOULD have duplicates — that's the point (100,000 of the same creature).
- **ALLOW_IF_STATS_DIFFER**: Same archetype is fine as long as the stat profile differs (which it naturally will since different barcodes produce different bytes).
- **REROLL_ON_SIGNATURE_MATCH**: If the exact 8-field signature matches an existing creature from a different source, reroll.
- **REROLL_ON_ANY_ARCHETYPE_MATCH**: For Legendary, even a partial match (same species+biome) triggers reroll to ensure every Legendary feels truly unique.

### 6.2 Deterministic Reroll

```python
for iteration in range(MAX_REROLL_ATTEMPTS):
    if iteration == 0:
        seed = SHA256(canonical_id)
    else:
        seed = SHA256(f"{canonical_id}|reroll|{iteration}")

    creature = generate_from_seed(seed)

    if not collides(creature, policy):
        creature.generation_iteration = iteration
        return creature

raise GenerationError("Exceeded max reroll attempts")
```

Still deterministic — same barcode always follows the same reroll path and arrives at the same creature.

---

## 7. Concurrency at Scale (100,000+ Simultaneous Users)

### 7.1 The Race Condition Problem

Two users scan different barcodes at the same millisecond. Both generate `LEGENDARY|SNOWLAND|DRAGON|ICE_DRAGON|ICE|HUGE|NOBLE|FROSTBORN`. Only one should get it (Legendary collision policy). Who wins?

### 7.2 Solution: Optimistic Locking with MongoDB

```python
async def register_creature(creature: CreatureCard) -> CreatureCard:
    # 1. Try to insert the source mapping (unique index on canonical_id)
    try:
        await db.source_registry.insert_one({
            "canonical_id": creature.source.canonical_id,
            "creature_id": creature.identity.creature_id,
        })
    except DuplicateKeyError:
        # Same barcode already registered — return existing creature
        existing = await db.source_registry.find_one({"canonical_id": creature.source.canonical_id})
        return await db.creatures.find_one({"creature_id": existing["creature_id"]})

    # 2. For collision-checked rarities, try to claim the signature
    if needs_collision_check(creature.classification.rarity):
        result = await db.creature_signatures.find_one_and_update(
            {"signature": creature.identity.creature_signature, "claimed": False},
            {"$set": {"claimed": True, "creature_id": creature.identity.creature_id}},
            upsert=True,  # Creates if doesn't exist
            return_document=ReturnDocument.AFTER,
        )
        if result["creature_id"] != creature.identity.creature_id:
            # Someone else claimed this signature first → reroll
            return await generate_with_reroll(creature.source, iteration=1)

    # 3. Atomically increment supply counters
    counter_result = await db.supply_counters.find_one_and_update(
        {"counter_key": f"rarity:{creature.classification.rarity}", "current_count": {"$lt": max_count}},
        {"$inc": {"current_count": 1}},
        return_document=ReturnDocument.AFTER,
    )
    if counter_result is None:
        # Supply cap hit → downgrade rarity
        return await generate_with_downgrade(creature)

    # 4. Persist the creature
    await db.creatures.insert_one(creature.dict())
    return creature
```

**Key MongoDB indexes:**
- `source_registry.canonical_id` — unique index (prevents duplicate source registration)
- `creature_signatures.signature` — unique index (prevents duplicate claims)
- `supply_counters.counter_key` — unique index

### 7.3 Why This Works at Scale

- **No distributed locks** — all concurrency is handled by MongoDB's atomic operations (`findOneAndUpdate`, unique indexes, `$inc`)
- **No Redis needed** — the counters and signatures are durable (must survive restarts)
- **Deterministic reroll** — if two users collide, the loser gets a deterministic alternative, not a random one
- **Idempotent** — scanning the same barcode twice always returns the same creature (source_registry lookup)

### 7.4 Performance Considerations

At 100K simultaneous generations:
- Each generation is ~3 MongoDB operations (source check, signature claim, counter increment)
- MongoDB handles 50K+ ops/sec on modest hardware
- The SHA-256 hash + byte picking is pure CPU, negligible (<1ms)
- The bottleneck is image generation (LLM call), which we handle async (see Section 8)

---

## 8. LLM Image Generation Integration

### 8.1 The Problem

Generating artwork for every creature via LLM is expensive and slow (~5-15 seconds per image). We can't block the user.

### 8.2 Solution: Generate-on-First-Scan, Cache Forever

```
Flow:
1. User scans barcode
2. Character Service generates creature definition (instant, <100ms)
3. Check: does artwork exist in Image Service for this creature_id?
   YES → return creature + image URL immediately
   NO  → return creature with placeholder art + queue art generation
4. Background job calls LLM Service with creature description prompt
5. LLM returns image → store in Image Service
6. Update creature record with image_id
7. Next time anyone scans this barcode → art is already cached
```

### 8.3 Art Prompt Generation

The creature's classification fields become an LLM prompt:

```python
def build_art_prompt(creature):
    return (
        f"A collectible trading card illustration of a {creature.classification.size.lower()} "
        f"{creature.presentation.name}, a {creature.classification.variant.lower()} "
        f"{creature.classification.species.lower()} creature living in the "
        f"{creature.classification.biome.replace('_', ' ').lower()}. "
        f"Element: {creature.classification.element.lower()}. "
        f"Temperament: {creature.classification.temperament.lower()}. "
        f"Colours: {creature.presentation.flavor_profile.primary_color} and "
        f"{creature.presentation.flavor_profile.secondary_color}. "
        f"Fantasy wildlife art style, detailed, painterly."
    )
```

### 8.4 Deduplication

Since the same barcode always produces the same creature_id, and we check for existing artwork before generating, we **never send duplicate LLM calls** for the same creature. Even if 10,000 users scan the same barcode, the LLM is called exactly once.

---

## 9. User Collection Model

A creature *definition* is global. A creature *instance* is per-user.

```json
// creatures collection (global, one per creature_id)
{
  "creature_id": "WF-RARE-FOREST-ELF-8A4C91B2",
  "source": { "canonical_id": "...", "code_type": "EAN_13", ... },
  "classification": { "rarity": "RARE", "biome": "FOREST", ... },
  "presentation": { "name": "Mossbound Grove Elf", ... },
  "attributes": { "power": 52, ... },
  "image_id": "img-abc123",
  "season": "v1",
  "claimed_by": "firebase-uid-abc123",
  "claimed_at": "2026-03-06T...",
  "status": "claimed",    // "claimed" | "released" | "unclaimed"
  "created_at": "2026-03-06T..."
}

// user_collections collection (per-user ownership)
{
  "user_id": "firebase-uid-abc123",
  "creature_id": "WF-RARE-FOREST-ELF-8A4C91B2",
  "obtained_at": "2026-03-06T...",
  "obtained_via": "barcode_scan",    // "barcode_scan" | "marketplace_purchase" | "gift" | "released_reclaim"
  "source_canonical_id": "EAN_13|5012345678900|WILDERNESS_FRIENDS|v1",
  "is_tradeable": true,              // can be listed on marketplace
  "listed_for_sale": false           // currently on marketplace
}
```

This means:
- **First scanner claims** the creature at its natural rarity (D2/D7)
- Subsequent scanners of the same barcode get a deterministic Common variant
- A user can own multiple creatures (from different barcodes)
- The `obtained_via` field tracks provenance (scan, marketplace purchase, gift)
- The `status` field supports the marketplace: "released" creatures can be re-claimed or purchased
- The `is_tradeable` / `listed_for_sale` fields prepare for the future Creature Store
- The collection is lightweight (references + metadata) — creature data lives in the global registry

---

## 10. Generation Config (Versioned, Not Hardcoded)

All enums and mappings live in a YAML config file, not in code:

```
character-service/
  config/
    generation_v1.yml    # All enums, maps, weights for v1
    generation_v2.yml    # Future expansion (new biomes, species, etc.)
```

Example structure:
```yaml
version: "v1"
namespace: "WILDERNESS_FRIENDS"

rarity_weights:
  COMMON:    { min: 0, max: 69 }
  UNCOMMON:  { min: 70, max: 89 }
  RARE:      { min: 90, max: 96 }
  EPIC:      { min: 97, max: 98 }
  LEGENDARY: { min: 99, max: 99 }

supply_caps:
  COMMON:    null
  UNCOMMON:  100000
  RARE:      25000
  EPIC:      5000
  LEGENDARY: 500

biomes:
  - FOREST
  - DEEP_FOREST
  - ENCHANTED_FOREST
  # ... 45 total

species:
  - id: ELF
    family: ELF
  - id: WOLF
    family: BEAST
  # ... 40+ total

biome_species_map:
  FOREST: [ELF, DRYAD, SPRIGGAN, TREANT, WOLF, STAG, OWL, FOX, BEAR]
  SWAMP: [TROLL, HYDRA, SERPENT, GOBLIN, NAGA, WRAITH, BOAR]
  # ...

subtype_map:
  ELF:
    FOREST: [WOODLAND_ELF, MOSS_ELF, GROVE_ELF]
    SNOWLAND: [SNOW_ELF, FROST_ELF, WHITEBARK_ELF]
    DEFAULT: [WANDERING_ELF, EXILE_ELF]
  # ...

collision_policy:
  COMMON:    ALLOW
  UNCOMMON:  ALLOW
  RARE:      ALLOW_IF_STATS_DIFFER
  EPIC:      REROLL_ON_SIGNATURE_MATCH
  LEGENDARY: REROLL_ON_ANY_ARCHETYPE_MATCH
```

**Why YAML not DB?** The generation rules must be **immutable per version**. If you change them in a DB, old barcodes could produce different creatures. By file-versioning, v1 is frozen forever. v2 can add new content without breaking v1 creatures.

---

## 11. Gateway Integration

Add to `services/node-gateway/src/config/services.js`:

```javascript
characters: {
  url: 'http://character-service:5002',
  pathPrefix: '/characters',
}
```

Gateway routes:
- `POST /api/characters/generate` — scan a barcode, get a creature
- `GET /api/characters/:creature_id` — get a creature by ID
- `GET /api/characters/collection/:user_id` — get user's collection
- `GET /api/characters/supply` — current supply cap status
- `GET /api/characters/health` — health check

---

## 12. Testing Strategy

### 12.1 Unit Tests (~30)

- **Normalisation**: UPC-A valid/invalid, EAN-13 valid/invalid, QR, edge cases
- **Seed derivation**: same input → same hash, different input → different hash
- **Rarity from byte**: verify all 100 byte values map to correct tiers
- **Biome-species constraint**: verify no invalid species-biome combos
- **Stat ranges**: verify stats stay within rarity bounds
- **Name generation**: verify templates produce valid strings
- **Signature building**: verify format is correct

### 12.2 Integration Tests (~25)

- **Full generation flow**: barcode in → creature out → verify all fields
- **Idempotency**: same barcode twice → same creature
- **Collision reroll**: two barcodes producing same signature → second gets rerolled
- **Supply cap**: generate past cap → verify downgrade
- **User collection**: add to collection, list collection, duplicate handling
- **Concurrent generation**: simulate N simultaneous requests

### 12.3 The Big Barcode Stress Test

This is the test you specifically asked for. A dedicated test that:

1. **Generates 500+ barcodes** (mix of UPC-A and EAN-13, using real-world format patterns)
2. **Runs them all through the generation pipeline**
3. **Asserts:**
   - Every barcode produces a valid creature
   - Same barcode run twice produces identical creature
   - Rarity distribution roughly matches weights (±5% with 500 samples)
   - No two different barcodes produce the same creature_id
   - No LEGENDARY creatures exceed supply cap
   - Biome-species constraints are always respected
   - All stats are within rarity-appropriate ranges
4. **Intentional duplicate test:**
   - Feed the same barcode 10 times → verify it returns the same creature every time
   - Feed two barcodes known to produce same initial signature → verify reroll resolves it
5. **Reports:** distribution stats, any collisions found, cap usage

This test runs inside Docker like all others:
```bash
docker-compose exec -T character-service pytest tests/integration/test_barcode_stress.py -v
```

### 12.4 Mobile Dev Tools Screen

A new dev tools sub-screen: **"Character Generator Test"**
- Text input for barcode value + code type picker
- "Generate" button → shows resulting creature JSON
- "Batch Generate (100)" → generates 100 random barcodes, shows distribution pie chart
- "Duplicate Test" → scans same barcode 5 times, shows all results match

---

## 13. File Structure (New Service)

```
services/character-service/
├── Dockerfile
├── requirements.txt
├── config/
│   └── generation_v1.yml        # All enums, maps, weights
├── app/
│   ├── main.py                  # FastAPI app with lifespan
│   ├── config.py                # Pydantic settings
│   ├── database.py              # MongoDB connection
│   ├── models/
│   │   ├── creature.py          # CreatureCard, Source, Classification, etc.
│   │   ├── registry.py          # SourceRegistry, CreatureSignature, SupplyCounter
│   │   └── collection.py        # UserCollection
│   ├── services/
│   │   ├── normalisation.py     # Code normalisation (UPC, EAN, QR)
│   │   ├── generator.py         # Deterministic generation algorithm
│   │   ├── registry.py          # Registry + collision + supply cap logic
│   │   ├── collection.py        # User collection management
│   │   └── art_orchestrator.py  # LLM prompt building + image gen + caching
│   └── routes/
│       ├── health.py            # GET /health
│       ├── generate.py          # POST /generate (main endpoint)
│       ├── creatures.py         # GET /:creature_id
│       ├── collection.py        # GET /collection/:user_id
│       └── supply.py            # GET /supply
└── tests/
    ├── conftest.py
    ├── unit/
    │   ├── test_normalisation.py
    │   ├── test_generator.py
    │   └── test_models.py
    └── integration/
        ├── test_generate_routes.py
        ├── test_collection_routes.py
        ├── test_registry.py
        └── test_barcode_stress.py   # The big 500-barcode test
```

---

## 14. Build Order

```
Phase 5a: Character Service Core
  1. Dockerfile + requirements + docker-compose entry
  2. Config loader (generation_v1.yml parser)
  3. Normalisation service (UPC/EAN/QR)
  4. Generator service (seed → creature, deterministic)
  5. Models (Pydantic)
  6. Unit tests for normalisation + generator

Phase 5b: Registry & Supply Caps
  7. Registry service (source registry, signature registry, supply counters)
  8. Collision resolution logic
  9. Supply cap enforcement + downgrade
  10. Integration tests (full flow, idempotency, collisions, caps)

Phase 5c: Gateway + API Routes
  11. FastAPI routes (generate, creatures, collection, supply, health)
  12. Gateway proxy entry + auth middleware
  13. Mobile SDK module (services/characters.ts)
  14. Integration tests for routes

Phase 5d: Art Generation Pipeline
  15. Art prompt builder
  16. LLM Service integration (call /generate/image)
  17. Image Service integration (store result)
  18. Cache check (don't re-generate)

Phase 5e: Testing & Dev Tools
  19. Barcode stress test (500+ barcodes)
  20. Mobile dev tools screen (Character Generator Test)
  21. Full 245+ test suite verification
```

---

## 15. Design Decisions (Resolved)

### D1: Include Common tier — YES
All 5 tiers active: Common (70%), Uncommon (20%), Rare (7%), Epic (2%), Legendary (1%). Common at 70% makes the higher tiers feel genuinely special.

### D2: Same barcode, different users — First scanner claims
The **first user** to scan a barcode claims the creature at its natural rarity. Subsequent scanners of the **same barcode** get a deterministic Common variant derived from `SHA256(canonical_id + "|claimed_variant")`. The original creature definition is stored globally (needed for marketplace display), but marked as claimed by the first scanner. This prevents barcode sharing to duplicate rares.

### D3: Supply caps — Per-season
Each season gets its own supply pool (e.g., Season 1: 500 Legendaries, Season 2: fresh 500). The generation version changes per season (v1 → v2), which changes the namespace in the canonical ID — so the **same barcode produces a different creature in each season**. Old-season creatures become permanently scarce and tradeable on the marketplace.

### D4: Art generation timing — On first scan (Option A)
Generate artwork on the first scan. User gets creature definition immediately (<100ms) with placeholder art, then real art arrives via background generation (~10s). Art is cached forever — subsequent scans return the cached image instantly.

### D5: Rare tier collision policy — ALLOW_IF_STATS_DIFFER (keep as-is)
Multiple Rare creatures of the same archetype (e.g., two Rare Grove Wolves) are allowed as long as their stat profiles differ (which they naturally will from different barcodes). This makes Rare feel "uncommon but not one-of-a-kind." True uniqueness is reserved for Epic (unique signature) and Legendary (unique archetype).

### D6: Generation config — Full enum set for v1
Ship with the complete set: ~45 biomes, ~60 creature types, ~45 beasts, ~25 variant prefixes. The combinatorial richness (146K+ archetypes) is a feature — it makes finding duplicates rare even at Common tier.

### D7: Barcode ownership — First scanner claims, others get Common variant
First scanner claims the creature at its natural rarity. Subsequent scanners of the same barcode get a deterministic Common variant. This prevents sharing barcodes to duplicate rares while still giving latecomers *something* (a Common creature). Combined with scan limits (see Section 17), this prevents both sharing abuse and farming abuse.

### D8: Art prompt system — Deferred to dedicated design pass
The `build_art_prompt()` function is a placeholder. Before Phase 5d (Art Generation Pipeline), a dedicated planning session will design the prompt system incorporating: different artist styles, style tokens seeded from creature bytes, style variety per biome/rarity, and consistent visual identity across the collection.

---

## 16. Scan Economy & Monetisation (Future — Informs Architecture)

This section captures the strategic direction that the character-service must be **architecturally prepared for**, even though the full implementation is a future phase.

### 16.1 The Problem: Preventing Farming & Hoarding

Without limits, a user could walk through a supermarket scanning every barcode, claiming all the rares. The "first scanner claims" model (D2/D7) prevents *sharing* rares, but doesn't prevent *farming*.

### 16.2 Scan Economy Model

```
Free tier:     X scans/month (e.g., 5)
Bronze sub:    Y scans/month (e.g., 20)
Silver sub:    Z scans/month (e.g., 50)
Gold sub:      Unlimited scans/month
Scan packs:    Buy N additional scans (e.g., 10 for $1.99)
```

### 16.3 Rarity Retention Limits (Per Period)

Even with unlimited scans, cap how many Rare+ creatures can be *kept* per month:

```
Free tier:     1 Rare, 0 Epic, 0 Legendary per month
Bronze:        3 Rare, 1 Epic, 0 Legendary per month
Silver:        5 Rare, 2 Epic, 1 Legendary per month
Gold:          10 Rare, 5 Epic, 2 Legendary per month
```

If a user exceeds their rarity retention limit, the creature is still generated (deterministic — can't be changed), but they're offered the choice to: keep it (uses a retention slot), release it back to the pool (someone else can claim it later), or buy an extra retention slot.

### 16.4 Architecture Implications

The character-service needs:
- `scan_allowance` check before processing a scan (calls permissions-service or commerce-service)
- `rarity_retention` tracking per user per period
- `released_creatures` collection — creatures that were generated but released back, available for marketplace or re-discovery
- Integration with existing subscription model in commerce-service

### 16.5 Marketplace / Creature Store (Future)

When supply caps are exhausted for a creature archetype:
- Users who try to generate it are told "This creature is no longer available for generation"
- They can purchase it from the **Creature Store** (marketplace)
- Sellers list creatures they own, set prices
- The platform takes a cut (standard marketplace model)
- This creates real economic value for rare finds

This is a future phase but the data model (D2 — global creature definition + per-user instance ownership) is designed to support it.

---

## 17. What's NOT In Scope For Phase 5

- Scan economy enforcement (limits, packs, subscriptions) — Phase 6+
- Creature marketplace / store — Phase 6+
- Battle/gameplay mechanics using card stats
- Push notifications for art completion
- Admin panel for managing supply caps
- Artist style system for art prompts — dedicated design pass before Phase 5d
- Seasonal content rotation (v2 generation config)

These are future phases, but the character-service is designed to accommodate all of them. The data model, scan tracking, and ownership system are built with these features in mind.
