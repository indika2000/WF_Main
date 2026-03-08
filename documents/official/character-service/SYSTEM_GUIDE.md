# Character Service — System Guide

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Generation Algorithm](#generation-algorithm)
4. [Data Models](#data-models)
5. [Configuration Schema](#configuration-schema)
6. [Season Changes](#season-changes)
7. [World Changes](#world-changes)
8. [API Endpoints](#api-endpoints)
9. [Collision Handling](#collision-handling)
10. [Supply Management](#supply-management)
11. [MongoDB Collections & Indexes](#mongodb-collections--indexes)
12. [File Structure](#file-structure)

---

## Overview

The Character Service is a FastAPI application (port 5002) that deterministically generates collectible creature cards from barcode scans. The core principle is **same input → same output**: a given barcode always produces the same creature, regardless of when or where it's scanned.

**Key properties:**
- Pure deterministic generation (SHA-256 based, no randomness)
- Config-driven world schema (species, biomes, elements, etc.)
- Rarity-based stat scaling with supply caps
- Collision detection and rerolling for rare+ creatures
- Season isolation (version changes produce entirely different creatures)
- World isolation (different namespaces produce entirely different creatures)

---

## Architecture

```
Barcode Scan
     │
     ▼
┌─────────────────┐
│  Normalisation   │  Validate format, strip whitespace
│  (normalise())   │  UPC-A: 12 digits, EAN-13: 13 digits, QR: any string
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Canonical ID     │  "{CODE_TYPE}|{NORMALISED}|{NAMESPACE}|{VERSION}"
│ (build_canonical)│  e.g. "EAN_13|5012345678900|WILDERNESS_FRIENDS|v1"
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ SHA-256 Hash     │  canonical_id → 32 bytes (256 bits)
│ (_hash_seed())   │  Completely different output for any input change
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Byte Allocation  │  Each byte maps to one creature attribute
│ (generate_       │  byte[0]→rarity, byte[1]→biome, byte[3]→species...
│  creature())     │  Config lists + modulo = deterministic pick
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Registry         │  Check collisions, enforce supply caps
│ (register())     │  Persist to MongoDB if new
└─────────────────┘
```

---

## Generation Algorithm

### Byte Allocation Map

The SHA-256 hash produces 32 bytes. Each byte is allocated to a specific creature attribute:

| Byte(s) | Attribute | Selection Method |
|---------|-----------|-----------------|
| `[0]` | Rarity | `byte % 100` → rarity weight ranges |
| `[1]` | Biome | Weighted or uniform selection via `config.get_biome()` |
| `[2]` | *(reserved)* | Family derived from species |
| `[3]` | Species | `byte % len(eligible_species)` — constrained by biome |
| `[4]` | Sub-type | `byte % len(subtypes)` — constrained by species + biome |
| `[5]` | Element | `byte % len(elements)` |
| `[6]` | Temperament | `byte % len(temperaments)` |
| `[7]` | Size | `byte % len(sizes)` |
| `[8]` | Variant | `byte % len(variants)` |
| `[9]` | Role | `byte % len(roles)` — for title generation |
| `[10]` | Primary colour | `byte % len(primary_colors)` |
| `[11]` | Secondary colour | `byte % len(secondary_colors)` |
| `[12]` | Sigil | `byte % len(sigils)` |
| `[13]` | Frame style | `byte % len(frame_styles)` |
| `[14-20]` | Stats (7) | `stat_min + (byte % stat_range_size)` |
| `[21]` | Domain | `byte % len(domains)` — for title generation |
| `[22-31]` | *(reserved)* | Future expansion |

### Constraint Chain

Species and subtype selection is constrained by previously selected attributes:

```
biome → eligible_species (from biome_species_map)
species → family (from species list)
species + biome → subtypes (from subtype_map, with DEFAULT fallback)
```

### Determinism Guarantee

The algorithm is a pure function with no randomness:
- Same `canonical_id` → same SHA-256 hash → same byte values → same creature
- Changing any part of the canonical ID (code type, value, namespace, version) produces a completely different hash
- Rerolls append `|reroll|{iteration}` to the canonical ID, producing a new hash

---

## Data Models

### CreatureCard

The complete creature definition stored in MongoDB.

| Section | Field | Type | Example |
|---------|-------|------|---------|
| **Identity** | `creature_id` | string | `"WF-v1-RARE-FOREST-ELF-8A4C91B2"` |
| | `creature_signature` | string | `"RARE\|FOREST\|ELF\|GROVE_ELF\|EARTH\|MEDIUM\|CAUTIOUS\|MOSSBOUND"` |
| **Source** | `canonical_id` | string | `"EAN_13\|5012345678900\|WILDERNESS_FRIENDS\|v1"` |
| | `code_type` | string | `"EAN_13"`, `"UPC_A"`, `"QR"` |
| | `raw_value` | string | Original scanned value |
| **Classification** | `rarity` | string | `"COMMON"` through `"LEGENDARY"` |
| | `biome` | string | From config biomes list |
| | `family` | string | Derived from species |
| | `species` | string | From config species list |
| | `sub_type` | string | From config subtype_map |
| | `element` | string | From config elements list |
| | `temperament` | string | From config temperaments list |
| | `size` | string | From config sizes list |
| | `variant` | string | From config variants list |
| **Presentation** | `name` | string | Generated from `name_template` |
| | `title` | string | Generated from `title_template` |
| | `primary_color` | string | From config primary_colors list |
| | `secondary_color` | string | From config secondary_colors list |
| | `sigil` | string | From config sigils list |
| | `frame_style` | string | From config frame_styles list |
| **Attributes** | `power` | int | 10-100 (rarity-scaled) |
| | `defense` | int | 10-100 |
| | `agility` | int | 10-100 |
| | `wisdom` | int | 10-100 |
| | `ferocity` | int | 10-100 |
| | `magic` | int | 10-100 |
| | `luck` | int | 10-100 |
| **Meta** | `season` | string | Config version (e.g. `"v1"`) |
| | `status` | string | `"unclaimed"`, `"claimed"`, `"released"` |
| | `generation_iteration` | int | 0 = no reroll, 1+ = rerolled |

### Creature ID Format

```
{id_prefix}-{version}-{rarity}-{biome}-{species}-{hash_fragment}
```

Examples:
- WildernessFriends: `WF-v1-RARE-FOREST-ELF-8A4C91B2`
- CyberFriends: `CF-c1-EPIC-NEON_DISTRICT-ANDROID-3F2A1C9D`

---

## Configuration Schema

The generation config is a YAML file that defines the complete world schema. All lists, maps, and templates are config-driven.

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Season identifier (e.g. `"v1"`, `"v2"`, `"c1"`) |
| `namespace` | string | World namespace (e.g. `"WILDERNESS_FRIENDS"`, `"CYBER_FRIENDS"`) |
| `rarity_weights` | dict | Maps rarity → `{min, max}` range (covers 0-99) |
| `supply_caps` | dict | Maps rarity → max count (`null` = unlimited) |
| `collision_policy` | dict | Maps rarity → collision handling strategy |
| `stat_ranges` | dict | Maps rarity → `{min, max}` stat bounds |
| `stat_names` | list | Ordered stat names (matched to bytes 14-20) |
| `biomes` | list | All biome identifiers |
| `species` | list | All species with `{id, family}` |
| `biome_species_map` | dict | Maps biome → list of eligible species |
| `subtype_map` | dict | Maps species → biome → subtypes (with DEFAULT) |
| `elements` | list | Element types |
| `temperaments` | list | Temperament types |
| `sizes` | list | Size categories |
| `variants` | list | Variant prefixes |
| `primary_colors` | list | Primary colour options |
| `secondary_colors` | list | Secondary colour options |
| `sigils` | list | Sigil types |
| `frame_styles` | list | Frame style options |
| `roles` | list | Title role words |
| `domains` | list | Title domain phrases |

### Optional Fields (World Flexibility)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id_prefix` | string | `"WF"` | Prefix for creature IDs |
| `name_template` | string | `"{variant} {sub_type}"` | Python format string for creature name |
| `title_template` | string | `"The {role} of {domain}"` | Python format string for creature title |
| `biome_weights` | dict | `null` | Maps biome → integer weight for biased selection |
| `max_reroll_attempts` | int | `10` | Max collision rerolls before downgrade |

### Template Variables

The `name_template` and `title_template` support these variables:

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `{variant}` | Variant prefix (title case) | `"Frostborn"` |
| `{sub_type}` | Sub-type name (title case) | `"Ice Dragon"` |
| `{role}` | Title role | `"Warden"` |
| `{domain}` | Title domain | `"Hollow Pines"` |
| `{species}` | Species name (title case) | `"Dragon"` |
| `{biome}` | Biome name (title case) | `"Frozen Tundra"` |
| `{element}` | Element name (title case) | `"Ice"` |
| `{rarity}` | Rarity tier (title case) | `"Legendary"` |

### Biome Weights

When `biome_weights` is set, biome selection uses weighted distribution instead of uniform:

```yaml
# Ocean-themed season — aquatic biomes 5x more likely
biome_weights:
  OCEAN: 5
  DEEP_OCEAN: 5
  CORAL_REEF: 5
  RIVER: 5
  LAKE: 5
  # All unlisted biomes default to weight 1
```

**Algorithm:** Pre-computed cumulative weight table. `byte_val % total_weight` → walk table to find biome.

**Validation rules:**
- Every biome in `biome_weights` must exist in `biomes` list
- All weights must be positive integers (≥1)
- Unlisted biomes automatically get weight 1

---

## Season Changes

A "season" represents a themed variant of the same world. Same species, biomes, and rules — but with weighted distribution and a different version string to produce unique creatures.

### How to Create a New Season

1. **Copy the current config** (e.g. `generation_v1.yml` → `generation_v2.yml`)
2. **Change the version**: `version: "v2"`
3. **Add biome weights** (optional): Bias toward thematic biomes
4. **Deploy** the new config file and update `GENERATION_CONFIG_PATH`

### What Changes Between Seasons

| Aspect | Changes? | Why |
|--------|----------|-----|
| Canonical ID | Yes | Version is part of the canonical ID |
| SHA-256 hash | Yes | Different canonical ID → completely different hash |
| All creature attributes | Yes | Different hash bytes → different picks |
| Creature IDs | Yes | Version included in ID format |
| Species/biome lists | No | Same world, same content |
| Biome distribution | Optional | Via `biome_weights` |

### Season Isolation Guarantee

The same barcode scanned in v1 and v2 produces **completely different creatures** because:
```
v1: "EAN_13|5012345678900|WILDERNESS_FRIENDS|v1" → SHA-256 → creature A
v2: "EAN_13|5012345678900|WILDERNESS_FRIENDS|v2" → SHA-256 → creature B
```

The SHA-256 avalanche effect means even a single character change produces an entirely unrelated hash.

### Example: Ocean-Themed Season

```yaml
version: "v2"
namespace: "WILDERNESS_FRIENDS"

# Same rarity_weights, species, biomes, etc. as v1

biome_weights:
  SWAMP: 5
  MANGROVE_SWAMP: 5
  BOG: 5
  OCEAN: 5
  DEEP_OCEAN: 5
  CORAL_REEF: 5
  RIVER: 5
  LAKE: 5
  WATERFALL: 5
  ISLAND: 5
  COAST: 5
```

**Result:** ~62% of creatures appear in aquatic biomes (vs ~24% uniform in v1).

---

## World Changes

A "world" is a completely different theme with its own species, biomes, elements, and lore. Think WildernessFriends (fantasy) vs CyberFriends (sci-fi).

### How to Create a New World

1. **Create a new config YAML** with entirely different content:

```yaml
version: "c1"
namespace: "CYBER_FRIENDS"
id_prefix: "CF"
name_template: "{variant} {sub_type}"
title_template: "{role} of {domain}"

biomes:
  - NEON_DISTRICT
  - ORBITAL_STATION
  - CYBERSPACE
  # ... completely different biomes

species:
  - { id: ANDROID, family: ANDROID }
  - { id: BATTLE_MECH, family: MECH }
  # ... completely different species

elements:
  - PLASMA
  - EMP
  - QUANTUM
  # ... completely different elements

# Full biome_species_map, subtype_map, etc.
```

2. **Deploy** with `GENERATION_CONFIG_PATH` pointing to the new file

### World vs Season Comparison

| Feature | Season Change | World Change |
|---------|--------------|--------------|
| Namespace | Same | Different |
| Version | Different | Different |
| Species list | Same | Completely different |
| Biome list | Same | Completely different |
| Elements | Same | Completely different |
| Config file | Modified copy | New file from scratch |
| ID prefix | Same (`WF-`) | Different (`CF-`) |
| Name/title templates | Same | Can be customized |
| Creature overlap | Zero (hash isolation) | Zero (namespace + hash isolation) |

### World Isolation Guarantee

Different worlds use different namespaces in the canonical ID:
```
WF: "EAN_13|5012345678900|WILDERNESS_FRIENDS|v1" → SHA-256 → WF creature
CF: "EAN_13|5012345678900|CYBER_FRIENDS|c1"      → SHA-256 → CF creature
```

Even if by coincidence the hash bytes were identical, the creatures would differ because they index into completely different species/biome/element lists.

### Checklist for a Valid World Config

- [ ] `version` — unique version identifier
- [ ] `namespace` — unique world namespace
- [ ] `id_prefix` — unique creature ID prefix (2-4 chars recommended)
- [ ] `rarity_weights` — ranges covering 0-99 with no gaps
- [ ] `supply_caps` — entry for every rarity tier
- [ ] `collision_policy` — entry for every rarity tier
- [ ] `stat_ranges` — entry for every rarity tier, `min < max`, values 0-100
- [ ] `stat_names` — list of 7 stat names (matched to bytes 14-20)
- [ ] `biomes` — list of unique biome identifiers
- [ ] `species` — list with `{id, family}` entries
- [ ] `biome_species_map` — every biome has species, every species in at least one biome
- [ ] `subtype_map` — every species has at least a `DEFAULT` subtype list
- [ ] `elements`, `temperaments`, `sizes`, `variants` — non-empty lists
- [ ] `primary_colors`, `secondary_colors`, `sigils`, `frame_styles` — non-empty lists
- [ ] `roles`, `domains` — non-empty lists

The `GenerationConfig` class validates all of these constraints at load time and raises `ValueError` with descriptive messages for any violations.

---

## API Endpoints

### POST /generate

Generate a creature from a barcode scan.

**Auth:** JWT required
**Body:**
```json
{
  "code_type": "EAN_13",
  "raw_value": "5012345678900"
}
```

**Response (new discovery):**
```json
{
  "success": true,
  "data": {
    "creature": { ... },
    "is_owner": true,
    "is_new_discovery": true,
    "is_claimed_variant": false
  }
}
```

**Behavior:**
- First scan: generates and registers the creature, adds to user's collection
- Same user, same barcode: returns existing creature (idempotent)
- Different user, same barcode: generates a Common claimed variant

### GET /creatures/{creature_id}

Look up a specific creature by ID.

### GET /collection

Get the authenticated user's creature collection with pagination.

**Query params:** `page` (default 1), `page_size` (default 20)

### GET /supply/status

Get current supply counts vs caps for all rarity tiers.

### GET /health, GET /health/detailed

Health check endpoints.

---

## Collision Handling

When a newly generated creature matches an existing one, the collision policy determines what happens:

| Policy | Behavior |
|--------|----------|
| `ALLOW` | No collision check — duplicates permitted |
| `ALLOW_IF_STATS_DIFFER` | Allow if stats are different, reroll otherwise |
| `REROLL_ON_SIGNATURE_MATCH` | Reroll if full signature matches |
| `REROLL_ON_ANY_ARCHETYPE_MATCH` | Reroll if rarity+biome+species matches |

Rerolling appends `|reroll|{N}` to the seed, producing a new hash. After `max_reroll_attempts` (default 10), the creature is downgraded to COMMON rarity.

---

## Supply Management

Each rarity tier has a per-season supply cap:

| Rarity | Default Cap |
|--------|-------------|
| COMMON | Unlimited |
| UNCOMMON | 100,000 |
| RARE | 25,000 |
| EPIC | 5,000 |
| LEGENDARY | 500 |

When a tier's cap is reached, new creatures of that rarity are downgraded to the next available tier.

---

## MongoDB Collections & Indexes

| Collection | Purpose | Unique Indexes |
|-----------|---------|---------------|
| `creatures` | All generated creatures | `identity.creature_id` |
| `source_registry` | Barcode → creature mapping | `canonical_id` |
| `user_collections` | User ownership records | `(user_id, creature_id)` |
| `supply_counters` | Per-rarity supply tracking | `(counter_key, season)` |

---

## File Structure

```
services/character-service/
├── app/
│   ├── main.py              # FastAPI app, lifespan, DB init
│   ├── config.py             # Service settings (BaseServiceConfig)
│   ├── database.py           # MongoDB connection
│   ├── models/
│   │   └── creature.py       # Pydantic models (CreatureCard, etc.)
│   ├── routes/
│   │   ├── health.py         # /health endpoints
│   │   └── generate.py       # /generate, /creatures, /collection, /supply
│   └── services/
│       ├── config_loader.py  # YAML config parser + GenerationConfig class
│       ├── generator.py      # Pure deterministic generation functions
│       ├── normalisation.py  # Barcode validation + canonical ID builder
│       └── registry.py       # DB persistence, collision detection, supply
├── config/
│   └── generation_v1.yml     # Production world config (WildernessFriends v1)
├── tests/
│   ├── conftest.py           # Shared fixtures (DB, auth, configs)
│   ├── fixtures/
│   │   ├── generation_v2_test.yml    # Ocean-themed season test config
│   │   └── generation_cyber_test.yml # CyberFriends world test config
│   ├── unit/
│   │   ├── test_config.py        # Config loading, validation, weights, templates
│   │   ├── test_generator.py     # Determinism, rarity, constraints, claimed variants
│   │   └── test_normalisation.py # Barcode format validation
│   └── integration/
│       ├── test_generate_routes.py   # API endpoint tests
│       ├── test_registry.py          # DB persistence, collisions, supply
│       ├── test_barcode_stress.py    # 500-barcode stress tests
│       ├── test_1000_barcodes.py     # 1000-barcode v1/v2 season tests
│       └── test_cross_world.py       # 1000-barcode cross-world tests
├── Dockerfile
└── requirements.txt
```
