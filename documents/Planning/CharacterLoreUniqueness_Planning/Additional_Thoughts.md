I want you to create a list of types of animals, creatures, fantasy creatures, fantasy monsters which could live in forests, swamps, mountains, and snow lands. I want you to provide a list of names and sub_type names based on the location they live, noting you could have  wood land elf who lives in a forest which is different to a snow elf, or mountain elf. As a pure example! But make it really exhaustive, even the types of lands I just said aren't exhaustive put them in a form of enum which the various varieties - go crazy and create 1000s

Lambert — this is a great foundation for your trading-card / QR-generated character universe. What you’re essentially building is a taxonomy + biome system, which is perfect for deterministic generation (barcode → seed → creature + biome variant).

Because you asked for “1000s”, the best format is structured enums + subtype generation rules rather than manually listing thousands. With a system like this you can easily generate 10k+ combinations while keeping everything consistent.

Below is a scalable framework you can plug directly into your JSON schema or generation algorithm.

1. Biome Enum (Primary Habitat)

These are the environment categories that determine creature subtype variants.

BiomeType = [
  "FOREST",
  "DEEP_FOREST",
  "ENCHANTED_FOREST",
  "JUNGLE",
  "SWAMP",
  "MARSH",
  "BOG",
  "RAINFOREST",
  "MANGROVE",
  "MOUNTAIN",
  "ALPINE",
  "VOLCANIC_MOUNTAIN",
  "CANYON",
  "CLIFFSIDE",
  "SNOWLAND",
  "TUNDRA",
  "GLACIER",
  "ICE_CAVES",
  "PERMAFROST",
  "DESERT",
  "DUNES",
  "BADLANDS",
  "OASIS",
  "SALT_FLATS",
  "PLAINS",
  "GRASSLAND",
  "SAVANNA",
  "STEPPE",
  "HILLS",
  "COAST",
  "BEACH",
  "CORAL_REEF",
  "DEEP_SEA",
  "ABYSSAL_OCEAN",
  "LAKE",
  "RIVER",
  "UNDERGROUND",
  "CRYSTAL_CAVES",
  "LAVA_TUNNELS",
  "MUSHROOM_FOREST",
  "SHADOW_REALM",
  "FAE_REALM",
  "CELESTIAL_REALM",
  "VOID",
  "ANCIENT_RUINS",
  "HAUNTED_LANDS",
  "ARCANE_WILDS"
]

~ 45 biome variants

2. Creature Base Types

These are species archetypes that can exist in multiple environments.

CreatureType = [
  "ELF",
  "DRAGON",
  "WYVERN",
  "DRAKE",
  "GRIFFIN",
  "UNICORN",
  "PEGASUS",
  "CENTAUR",
  "SATYR",
  "FAUN",
  "ENT",
  "TREANT",
  "DRYAD",
  "SPRIGGAN",
  "TROLL",
  "OGRE",
  "GIANT",
  "FROST_GIANT",
  "FIRE_GIANT",
  "CYCLOPS",
  "GOBLIN",
  "HOBGOBLIN",
  "BUGBEAR",
  "ORC",
  "KOBOLD",
  "GNOLL",
  "MERFOLK",
  "NAGA",
  "SIREN",
  "HARPY",
  "BASILISK",
  "COCKATRICE",
  "MANTICORE",
  "CHIMERA",
  "HYDRA",
  "KRAKEN",
  "LEVIATHAN",
  "SERPENT",
  "PHOENIX",
  "THUNDERBIRD",
  "ROC",
  "WYRM",
  "SHADOW_BEAST",
  "SPIRIT_BEAST",
  "GOLEM",
  "ELEMENTAL",
  "LICH",
  "WRAITH",
  "SPECTER",
  "BANSHEE",
  "WEREWOLF",
  "WENDIGO",
  "YETI",
  "ABOMINATION",
  "SLIME",
  "MIMIC",
  "BEHEMOTH",
  "TITAN",
  "FAMILIAR",
  "ANCIENT_BEAST"
]

~ 60 base creature archetypes

3. Animal / Natural Beast Types

For more grounded fantasy wildlife.

BeastType = [
  "WOLF",
  "DIRE_WOLF",
  "FOX",
  "ARCTIC_FOX",
  "BEAR",
  "POLAR_BEAR",
  "ELK",
  "MOOSE",
  "DEER",
  "BOAR",
  "GIANT_BOAR",
  "OWL",
  "RAVEN",
  "EAGLE",
  "HAWK",
  "SNOW_OWL",
  "PANTHER",
  "TIGER",
  "LION",
  "SABERTOOTH",
  "HYENA",
  "BADGER",
  "WOLVERINE",
  "LYNX",
  "IBEX",
  "GOAT",
  "RAM",
  "MOUNTAIN_LION",
  "CROCODILE",
  "ALLIGATOR",
  "SERPENT",
  "GIANT_SPIDER",
  "SCORPION",
  "STAG",
  "FROG",
  "TOAD",
  "SALAMANDER",
  "LIZARD",
  "GIANT_TURTLE",
  "CRAB",
  "JELLYFISH",
  "OCTOPUS",
  "SQUID"
]

~ 45 creatures

4. Magical Variant Prefixes

These change the rarity / magical nature of the creature.

VariantPrefix = [
  "ANCIENT",
  "ELDER",
  "ARCANE",
  "SHADOW",
  "LIGHT",
  "CRYSTAL",
  "IRON",
  "GOLDEN",
  "SPECTRAL",
  "CURSED",
  "BLESSED",
  "FERAL",
  "ALPHA",
  "ROYAL",
  "PRIMAL",
  "RUNIC",
  "MYSTIC",
  "STORM",
  "EMBER",
  "FROST",
  "GLACIAL",
  "VENOMOUS",
  "LUMINOUS",
  "VOID",
  "ASTRAL"
]
5. Environmental Subtype Generator

Subtype naming pattern:

<Biome> + <Creature>

Examples:

Forest Variants

Woodland Elf

Deep Forest Troll

Moss Bear

Verdant Treant

Canopy Drake

Vine Hydra

Fern Dryad

Hollow Ent

Swamp Variants

Bog Troll

Marsh Hydra

Mire Serpent

Rotwood Treant

Mangrove Ent

Croakling Goblin

Sludge Elemental

Mire Wraith

Mountain Variants

Alpine Griffin

Cliffside Wyvern

Granite Golem

Stone Troll

Thunder Roc

Sky Drake

Peak Giant

Crag Serpent

Snow Variants

Snow Elf

Frost Troll

Ice Hydra

Glacier Dragon

Snow Wolf

Ice Wraith

Permafrost Giant

Blizzard Phoenix

6. Example Generated Creatures

Here are random examples from the system.

Shadow Bog Hydra

Crystal Alpine Wyvern

Ancient Woodland Griffin

Frost Canyon Troll

Ember Volcano Drake

Glacial Snowland Dragon

Royal Savannah Centaur

Spectral Haunted Banshee

Runic Crystal Cave Golem

Alpha Deep Forest Dire Wolf

Storm Coast Leviathan

Luminous Coral Reef Naga

Venomous Mangrove Serpent

Primal Jungle Tiger

Elder Tundra Yeti

7. How This Scales to Thousands

Combinations:

45 biomes
60 fantasy creatures
45 beasts
25 prefixes

Possible combos:

~130 creature bases
× 45 biomes
× 25 variants

≈ 146,000 unique creatures

So your barcode/QR seed could easily generate hundreds of thousands of deterministic characters.

8. JSON Example for Your Game

Example creature output from a barcode seed:

{
  "name": "Shadow Bog Hydra",
  "type": "HYDRA",
  "biome": "SWAMP",
  "variant": "SHADOW",
  "rarity": "EPIC",
  "attributes": {
    "strength": 84,
    "agility": 42,
    "intelligence": 51,
    "ferocity": 90
  }
}
9. Optional Extra Dimensions (Highly Recommended)

To make your world richer:

Enums for:

Temperament
AGGRESSIVE
PASSIVE
GUARDIAN
TRICKSTER
WISE
NOBLE
FERAL
Size
TINY
SMALL
MEDIUM
LARGE
COLOSSAL
TITANIC
Rarity
COMMON
UNCOMMON
RARE
EPIC
LEGENDARY
MYTHIC
10. A Cool Trick for Your Barcode System

If you hash the barcode:

seed = sha256(barcode)

Then split the hash:

byte1 → biome
byte2 → creature type
byte3 → variant
byte4 → rarity
byte5+ → attributes

This ensures:

✔ same barcode → same creature
✔ millions of possibilities
✔ deterministic generation

✅ If you'd like, I can also generate:

A MASSIVE JSON file with 5,000+ creatures already expanded
ready to drop into your card generator.

Or even better:

a procedural creature generator algorithm that fits perfectly with your rarity tiers (Uncommon / Rare / Epic / Legendary) you were discussing earlier.

I like the idea of this: a procedural creature generator algorithm that fits perfectly with your rarity tiers (Uncommon / Rare / Epic / Legendary), however, I want to make sure we are accounting for duplicates in using UPC, EAN, and have capacity for QR creation in the future to avoid duplicates, is that possible?

Yes — it’s possible, but the key is this:

do not treat UPC, EAN, and QR as if they are the same raw identifier space.
Instead, treat them as inputs into a canonical identity system.

That gives you:

deterministic generation

room for future QR-based characters

protection against accidental duplicates

control over rarity and biome logic

The core idea

Create a universal source ID made of:

code_type — UPC_A, EAN_13, QR, etc.

code_value — the actual scanned value

optional namespace — your game/world/product line

optional version — in case your generation rules evolve later

So instead of generating from just:

036000291452

you generate from:

UPC_A|036000291452|CAPS_AND_CAPES|v1

and later a QR might be:

QR|https://capsandcapes.com/card/dragon-001|CAPS_AND_CAPES|v1

These become different canonical inputs, so they will not collide unless you explicitly want them to.

Why this matters

A UPC and an EAN can sometimes represent related numbers, and QR codes can encode literally anything.

If you hash only the numeric part, you risk collisions like:

UPC value looks similar to part of an EAN

QR encodes a URL that contains a UPC

future code formats overlap with legacy numeric formats

But if you hash the typed canonical string, then:

UPC_A|123456789012

EAN_13|0123456789012

QR|123456789012

are all different inputs.

Best architecture

Use a two-layer model:

Layer 1: Canonical identity

This is the permanent unique identity of the scanned code.

{
  "source_type": "UPC_A",
  "source_value": "036000291452",
  "namespace": "CAPS_AND_CAPES",
  "version": "v1",
  "canonical_id": "UPC_A|036000291452|CAPS_AND_CAPES|v1"
}
Layer 2: Procedural generation

Hash the canonical ID and use the result to generate:

biome

creature family

subtype

rarity

stats

personality

visual traits

So:

sha256("UPC_A|036000291452|CAPS_AND_CAPES|v1")

becomes the seed.

That means the same code always creates the same creature.

How to avoid duplicates properly

There are really two kinds of duplicates:

1. Input duplicates

Two scans represent the same exact source code.

That is fine.
You usually want them to produce the same creature.

Example:

same UPC scanned twice

same QR scanned twice

Result: same canonical ID, same seed, same creature.

2. Output duplicates

Two different source codes generate the same creature result.

This is what you want to minimize.

You avoid that by:

using a large hash space

deriving many traits from different parts of the hash

optionally storing issued creature IDs in a registry

If your generator only picks from 10 biomes × 20 species × 4 rarities, duplicates will happen eventually because the output space is too small.

If your generator includes:

biome

family

subtype

rarity

temperament

elemental affinity

patterning

size

horns/wings/tail/body form

10+ stats

title/adjective set

then the output space becomes enormous.

Important truth about “avoiding duplicates”

You can get very close, but there are two different standards here:

A. Deterministic uniqueness of seed

This is easy.
Every canonical code can map to a unique seed.

B. Guaranteed uniqueness of final creature

This is only guaranteed if you either:

make the output space bigger than your expected code volume by a huge margin, and/or

keep a registry that checks whether a generated creature signature already exists

So the strongest design is:

generate creature from seed

create a creature_signature

check a registry

if collision exists, use a deterministic salt step

Example:

seed_0 = sha256(canonical_id)
signature_0 = generated creature summary

if signature_0 already exists for another canonical_id:
    seed_1 = sha256(canonical_id + "|reroll|1")
    regenerate

That gives you deterministic conflict resolution.

Best practice for UPC / EAN / QR together

Use a normalized scheme like this:

{
  "supported_code_types": [
    "UPC_A",
    "EAN_13",
    "QR"
  ],
  "canonical_format": "<CODE_TYPE>|<NORMALIZED_VALUE>|<NAMESPACE>|<VERSION>"
}
Normalization examples
UPC-A

numeric only

exactly 12 digits

preserve leading zeroes

UPC_A|036000291452|CAPS_AND_CAPES|v1
EAN-13

numeric only

exactly 13 digits

preserve leading zeroes

EAN_13|0036000291452|CAPS_AND_CAPES|v1
QR

QR is more flexible, so normalize carefully:

trim whitespace

optionally lowercase URLs if appropriate

optionally standardize URL query params

keep exact text if you want strict identity

QR|https://capsandcapes.com/creature/fire-drake-1|CAPS_AND_CAPES|v1
Recommendation: separate “external code” from “game identity”

This is the cleanest setup.

A scanned barcode or QR is just the source key.
Then you derive a game-native ID.

Example:

{
  "source": {
    "type": "EAN_13",
    "value": "5012345678900"
  },
  "canonical_id": "EAN_13|5012345678900|CAPS_AND_CAPES|v1",
  "seed_hash": "8a4c...",
  "creature_id": "CC-LEG-FROST-ELF-8A4C91",
  "name": "Frostveil Elf",
  "rarity": "Legendary",
  "biome": "SNOWLAND"
}

That way your world is not tightly coupled to barcode formats forever.

How rarity should work

You mentioned you do not want constant Epic or Legendary pulls.

That means rarity should not be random in a loose way.
It should be weighted deterministically from the seed.

For example:

0–69   -> Common
70–89  -> Uncommon
90–97  -> Rare
98–99  -> Epic
100    -> Legendary

Or for your preferred tiers only:

0–74   -> Uncommon
75–92  -> Rare
93–98  -> Epic
99     -> Legendary

Use one byte from the hash:

rarity_roll = hash_byte_1 % 100

This guarantees:

same code = same rarity

legendary remains rare

no reroll abuse unless you want special mechanics

Stronger duplicate control: creature signature

To detect final-output collisions, define a compact signature such as:

<rarity>|<biome>|<species>|<subtype>|<element>|<size>|<temperament>|<variant>

Example:

LEGENDARY|SNOWLAND|ELF|FROST_ELF|ICE|MEDIUM|WISE|ASTRAL

If another canonical code produces the same signature and you want every card to be unique, then use a deterministic tie-breaker.

You could also allow partial duplicates but make the final identity unique with:

serial suffix

title

stat profile

visual markings

lore seed

Example:

Frostveil Elf

Frostveil Elf of the Seventh Gale

Frostveil Elf, Moonbound Warden

So even if the family is similar, the full character is still unique.

Best long-term solution for QR future-proofing

Yes, absolutely possible.
I’d recommend this model:

Supported source enums
{
  "CodeType": [
    "UPC_A",
    "EAN_13",
    "QR",
    "INTERNAL_UUID",
    "CUSTOM_ALPHANUMERIC"
  ]
}

This gives you room later for:

your own printed card IDs

promo codes

event-exclusive scans

app-generated QR summons

seller/item IDs in Caps & Capes style ecosystems

My recommendation for your system

Use this rule:

A code does not directly equal a creature.

A code equals a seedable source identity.

Then the pipeline is:

scan code
-> normalize by code type
-> build canonical_id
-> hash canonical_id
-> derive rarity
-> derive biome
-> derive species
-> derive subtype
-> derive stats / visuals / lore
-> build creature signature
-> collision check
-> deterministic salt if needed
-> final creature
Practical pseudocode
import hashlib

def normalize_code(code_type: str, raw_value: str) -> str:
    value = raw_value.strip()

    if code_type == "UPC_A":
        digits = ''.join(ch for ch in value if ch.isdigit())
        if len(digits) != 12:
            raise ValueError("UPC_A must be 12 digits")
        return digits

    if code_type == "EAN_13":
        digits = ''.join(ch for ch in value if ch.isdigit())
        if len(digits) != 13:
            raise ValueError("EAN_13 must be 13 digits")
        return digits

    if code_type == "QR":
        return value

    raise ValueError("Unsupported code type")


def canonical_id(code_type: str, raw_value: str, namespace="CAPS_AND_CAPES", version="v1") -> str:
    normalized = normalize_code(code_type, raw_value)
    return f"{code_type}|{normalized}|{namespace}|{version}"


def seed_from_canonical(canonical: str) -> bytes:
    return hashlib.sha256(canonical.encode("utf-8")).digest()


def rarity_from_seed(seed: bytes) -> str:
    roll = seed[0] % 100
    if roll == 99:
        return "LEGENDARY"
    elif roll >= 93:
        return "EPIC"
    elif roll >= 75:
        return "RARE"
    return "UNCOMMON"
My honest recommendation on uniqueness

For your world, I would use:

deterministic generation from canonical ID

typed namespaces for UPC/EAN/QR

large trait space

registry-backed collision detection

deterministic reroll salt only if full signature collision occurs

That gives you the best of both worlds:

predictable

scalable

future-proof

QR compatible

safe from most duplicate problems

The one thing not to do

Do not do this:

seed = hash(raw_digits_only)

Because then:

UPC and EAN can overlap conceptually

QR text may accidentally map into the same value space

you lose source-type context

future expansion gets messy

Clean design summary

Use:

canonical_id = CODE_TYPE + "|" + NORMALIZED_VALUE + "|" + NAMESPACE + "|" + VERSION

Then:

seed = sha256(canonical_id)

Then derive:

rarity

biome

species

subtype

stats

visuals

lore

Then:

check signature collisions

deterministic salt reroll only if needed

Yes — this is very doable, and it’s actually a really strong fit for the creature-card world you’re building.

The next useful step is for me to draft a full JSON schema + deterministic generation spec for:

code normalization

rarity weighting

biome/species/subtype selection

collision handling

future QR support

so you have a blueprint you can wire into your app or card engine.

Yes, I like all your recommendations and your registry idea. Can you draft a full JSON schema + deterministic generation spec

Absolutely. Below is a full draft JSON schema + deterministic generation spec designed for your creature-card system, with support for:

UPC-A

EAN-13

QR

future custom/internal code types

deterministic generation

rarity control

biome-aware subtype generation

registry-backed collision handling

versioning for future evolution

I’m going to split this into 5 parts so it’s practical:

Conceptual data model

JSON schema draft

Generation enums / config

Deterministic generation spec

Example outputs

1) Conceptual model

A scanned code becomes a source identity, not directly a creature.

Pipeline:

raw scan
-> normalize by code type
-> canonical_id
-> seed hash
-> derive rarity
-> derive biome
-> derive family/species
-> derive subtype
-> derive traits/stats/visual markers
-> build creature signature
-> check registry
-> deterministic reroll if collision
-> persist final creature

You really want three IDs:

A. Source identity

The original scan identity.

UPC_A|036000291452|CAPS_AND_CAPES|v1
B. Creature instance ID

The unique generated creature record.

CC-RARE-FOREST-ELF-8A4C91B2
C. Creature signature

The structured identity used for collision checking.

RARE|FOREST|ELF|WOODLAND_ELF|NATURE|MEDIUM|WISE|MOSSBOUND
2) Draft JSON schema

This is a practical schema draft for a generated creature object.

{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://capsandcapes.com/schema/creature-card.v1.json",
  "title": "Creature Card",
  "type": "object",
  "required": [
    "schema_version",
    "namespace",
    "source",
    "identity",
    "generation",
    "classification",
    "presentation",
    "attributes",
    "registry"
  ],
  "properties": {
    "schema_version": {
      "type": "string",
      "const": "1.0.0"
    },
    "namespace": {
      "type": "string",
      "minLength": 1
    },
    "source": {
      "type": "object",
      "required": [
        "code_type",
        "raw_value",
        "normalized_value",
        "canonical_id"
      ],
      "properties": {
        "code_type": {
          "type": "string",
          "enum": [
            "UPC_A",
            "EAN_13",
            "QR",
            "INTERNAL_UUID",
            "CUSTOM_ALPHANUMERIC"
          ]
        },
        "raw_value": {
          "type": "string",
          "minLength": 1
        },
        "normalized_value": {
          "type": "string",
          "minLength": 1
        },
        "canonical_id": {
          "type": "string",
          "minLength": 1
        },
        "normalization_ruleset_version": {
          "type": "string",
          "default": "1.0.0"
        }
      },
      "additionalProperties": false
    },
    "identity": {
      "type": "object",
      "required": [
        "seed_hash_hex",
        "generation_iteration",
        "creature_id",
        "creature_signature"
      ],
      "properties": {
        "seed_hash_hex": {
          "type": "string",
          "pattern": "^[A-Fa-f0-9]{64}$"
        },
        "generation_iteration": {
          "type": "integer",
          "minimum": 0
        },
        "creature_id": {
          "type": "string",
          "minLength": 1
        },
        "creature_signature": {
          "type": "string",
          "minLength": 1
        }
      },
      "additionalProperties": false
    },
    "generation": {
      "type": "object",
      "required": [
        "generator_version",
        "rarity_roll",
        "selection_indices"
      ],
      "properties": {
        "generator_version": {
          "type": "string"
        },
        "rarity_roll": {
          "type": "integer",
          "minimum": 0,
          "maximum": 99
        },
        "selection_indices": {
          "type": "object",
          "required": [
            "biome_index",
            "family_index",
            "subtype_index",
            "element_index",
            "temperament_index",
            "size_index",
            "title_index"
          ],
          "properties": {
            "biome_index": { "type": "integer", "minimum": 0 },
            "family_index": { "type": "integer", "minimum": 0 },
            "subtype_index": { "type": "integer", "minimum": 0 },
            "element_index": { "type": "integer", "minimum": 0 },
            "temperament_index": { "type": "integer", "minimum": 0 },
            "size_index": { "type": "integer", "minimum": 0 },
            "title_index": { "type": "integer", "minimum": 0 }
          },
          "additionalProperties": false
        }
      },
      "additionalProperties": false
    },
    "classification": {
      "type": "object",
      "required": [
        "rarity",
        "biome",
        "family",
        "species",
        "sub_type",
        "element",
        "temperament",
        "size",
        "variant"
      ],
      "properties": {
        "rarity": {
          "type": "string",
          "enum": [
            "UNCOMMON",
            "RARE",
            "EPIC",
            "LEGENDARY"
          ]
        },
        "biome": {
          "type": "string"
        },
        "family": {
          "type": "string"
        },
        "species": {
          "type": "string"
        },
        "sub_type": {
          "type": "string"
        },
        "element": {
          "type": "string"
        },
        "temperament": {
          "type": "string"
        },
        "size": {
          "type": "string"
        },
        "variant": {
          "type": "string"
        },
        "tags": {
          "type": "array",
          "items": { "type": "string" }
        }
      },
      "additionalProperties": false
    },
    "presentation": {
      "type": "object",
      "required": [
        "name",
        "title",
        "flavor_profile"
      ],
      "properties": {
        "name": {
          "type": "string"
        },
        "title": {
          "type": "string"
        },
        "flavor_profile": {
          "type": "object",
          "required": [
            "primary_color",
            "secondary_color",
            "sigil",
            "frame_style"
          ],
          "properties": {
            "primary_color": { "type": "string" },
            "secondary_color": { "type": "string" },
            "sigil": { "type": "string" },
            "frame_style": { "type": "string" }
          },
          "additionalProperties": false
        },
        "lore_seed": {
          "type": "string"
        }
      },
      "additionalProperties": false
    },
    "attributes": {
      "type": "object",
      "required": [
        "power",
        "defense",
        "agility",
        "wisdom",
        "ferocity",
        "magic",
        "luck"
      ],
      "properties": {
        "power": { "type": "integer", "minimum": 1, "maximum": 100 },
        "defense": { "type": "integer", "minimum": 1, "maximum": 100 },
        "agility": { "type": "integer", "minimum": 1, "maximum": 100 },
        "wisdom": { "type": "integer", "minimum": 1, "maximum": 100 },
        "ferocity": { "type": "integer", "minimum": 1, "maximum": 100 },
        "magic": { "type": "integer", "minimum": 1, "maximum": 100 },
        "luck": { "type": "integer", "minimum": 1, "maximum": 100 }
      },
      "additionalProperties": false
    },
    "registry": {
      "type": "object",
      "required": [
        "collision_checked",
        "collision_resolved"
      ],
      "properties": {
        "collision_checked": {
          "type": "boolean"
        },
        "collision_resolved": {
          "type": "boolean"
        },
        "collision_resolution_mode": {
          "type": "string",
          "enum": [
            "NONE",
            "DETERMINISTIC_REROLL"
          ]
        },
        "first_seen_at": {
          "type": "string"
        }
      },
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}
3) Core enums and config

This is the config layer your generator should use.
This is where your “go crazy” worldbuilding becomes manageable.

3.1 Code type enum
{
  "CodeType": [
    "UPC_A",
    "EAN_13",
    "QR",
    "INTERNAL_UUID",
    "CUSTOM_ALPHANUMERIC"
  ]
}
3.2 Biome enum

You can expand this freely, but here is a strong starting base:

{
  "BiomeType": [
    "FOREST",
    "DEEP_FOREST",
    "ENCHANTED_FOREST",
    "JUNGLE",
    "SWAMP",
    "MARSH",
    "BOG",
    "MANGROVE",
    "MOUNTAIN",
    "ALPINE",
    "VOLCANIC_MOUNTAIN",
    "CLIFFSIDE",
    "CANYON",
    "SNOWLAND",
    "TUNDRA",
    "GLACIER",
    "ICE_CAVES",
    "DESERT",
    "DUNES",
    "OASIS",
    "PLAINS",
    "GRASSLAND",
    "SAVANNA",
    "HILLS",
    "RIVERLAND",
    "LAKELAND",
    "COAST",
    "DEEP_SEA",
    "ABYSS",
    "UNDERGROUND",
    "CRYSTAL_CAVES",
    "MUSHROOM_FOREST",
    "ANCIENT_RUINS",
    "HAUNTED_LANDS",
    "FAE_REALM",
    "SHADOW_REALM",
    "CELESTIAL_REALM",
    "ARCANE_WILDS",
    "VOID"
  ]
}
3.3 Family enum

This is the high-level creature grouping.

{
  "CreatureFamily": [
    "ELF",
    "BEAST",
    "DRAGONKIN",
    "GIANTKIN",
    "GOBLINKIN",
    "SPIRIT",
    "UNDEAD",
    "ELEMENTAL",
    "CONSTRUCT",
    "SERPENTKIN",
    "AQUATIC",
    "AVIAN",
    "FAE",
    "MONSTROSITY",
    "SHAPESHIFTER"
  ]
}
3.4 Species enum

This is a flatter list the family can draw from.

{
  "SpeciesType": [
    "ELF",
    "DRYAD",
    "SPRIGGAN",
    "TREANT",
    "WOLF",
    "DIRE_WOLF",
    "BEAR",
    "STAG",
    "OWL",
    "RAVEN",
    "FOX",
    "BOAR",
    "TROLL",
    "OGRE",
    "GIANT",
    "YETI",
    "ORC",
    "GOBLIN",
    "HOBGOBLIN",
    "KOBOLD",
    "DRAGON",
    "DRAKE",
    "WYVERN",
    "SERPENT",
    "HYDRA",
    "GRIFFIN",
    "ROC",
    "HARPY",
    "NAGA",
    "MERFOLK",
    "KRAKEN",
    "WRAITH",
    "BANSHEE",
    "LICH",
    "GOLEM",
    "ELEMENTAL",
    "MIMIC",
    "CHIMERA",
    "MANTICORE",
    "BASILISK",
    "WEREBEAST",
    "WENDIGO",
    "UNICORN",
    "PHOENIX"
  ]
}
3.5 Element enum
{
  "ElementType": [
    "NATURE",
    "ICE",
    "FIRE",
    "STONE",
    "STORM",
    "WATER",
    "SHADOW",
    "LIGHT",
    "POISON",
    "ARCANE",
    "VOID",
    "METAL"
  ]
}
3.6 Temperament enum
{
  "TemperamentType": [
    "WISE",
    "FERAL",
    "NOBLE",
    "TRICKSTER",
    "AGGRESSIVE",
    "PASSIVE",
    "GUARDIAN",
    "HUNTER",
    "BROODING",
    "CURIOUS"
  ]
}
3.7 Size enum
{
  "SizeType": [
    "SMALL",
    "MEDIUM",
    "LARGE",
    "HUGE",
    "COLOSSAL"
  ]
}
3.8 Variant enum

This is your style layer.

{
  "VariantType": [
    "MOSSBOUND",
    "FROSTBORN",
    "EMBERVEIN",
    "STONEHIDE",
    "SHADETOUCHED",
    "SUNHALLOWED",
    "THORNCLAD",
    "MISTWALKER",
    "RUNEBLOOD",
    "STORMCREST",
    "GLASSFANG",
    "MOONMARKED",
    "ROTROOT",
    "CRYSTALVEIL",
    "VOIDSCARRED"
  ]
}
3.9 Rarity weights

For your four-tier system:

{
  "RarityRules": {
    "UNCOMMON": { "min": 0, "max": 74 },
    "RARE": { "min": 75, "max": 92 },
    "EPIC": { "min": 93, "max": 98 },
    "LEGENDARY": { "min": 99, "max": 99 }
  }
}

This gives you:

75% Uncommon

18% Rare

6% Epic

1% Legendary

That feels pretty healthy for a collectible ecosystem.

4) Deterministic generation spec

This is the important part.

4.1 Canonical source identity

Every scan becomes a canonical string:

<CODE_TYPE>|<NORMALIZED_VALUE>|<NAMESPACE>|<GENERATOR_VERSION>

Example:

UPC_A|036000291452|CAPS_AND_CAPES|v1
4.2 Normalization rules
UPC_A

Rules:

strip whitespace

keep digits only

must be exactly 12 digits

preserve leading zeros

Example:

raw: " 036000291452 "
normalized: "036000291452"
EAN_13

Rules:

strip whitespace

keep digits only

must be exactly 13 digits

preserve leading zeros

Example:

raw: "0036000291452"
normalized: "0036000291452"
QR

Rules:

strip leading/trailing whitespace

do not collapse inner text

optionally apply URL normalization if you choose to later

best default: exact string identity

Example:

raw: "https://capsandcapes.com/card/forest-elf-001"
normalized: "https://capsandcapes.com/card/forest-elf-001"
INTERNAL_UUID / CUSTOM_ALPHANUMERIC

Rules:

trim whitespace

preserve case only if meaningful

otherwise uppercase or lowercase consistently

choose one policy and keep it fixed in version

4.3 Seed derivation

Hash the canonical ID with SHA-256:

seed_bytes = SHA256(canonical_id)
seed_hex = hex(seed_bytes)

This gives 32 bytes.
Use these bytes deterministically for selection.

Recommended byte allocation:

byte[0]   -> rarity roll
byte[1]   -> biome
byte[2]   -> family
byte[3]   -> species
byte[4]   -> subtype
byte[5]   -> element
byte[6]   -> temperament
byte[7]   -> size
byte[8]   -> variant
byte[9]   -> title
byte[10]  -> color primary
byte[11]  -> color secondary
byte[12]  -> sigil
byte[13]  -> frame style
byte[14]  -> power
byte[15]  -> defense
byte[16]  -> agility
byte[17]  -> wisdom
byte[18]  -> ferocity
byte[19]  -> magic
byte[20]  -> luck
byte[21+] -> lore and tie-break support
4.4 Rarity derivation
rarity_roll = byte[0] % 100

Apply:

0–74 => UNCOMMON

75–92 => RARE

93–98 => EPIC

99 => LEGENDARY

This is deterministic and stable.

4.5 Biome derivation
biome_index = byte[1] % len(BiomeType)
biome = BiomeType[biome_index]
4.6 Family and species derivation

You have two options:

Option A: fully open selection

Any species can appear in any biome.

Simple, but less believable.

Option B: biome-constrained selection

This is the better design.

Create a mapping:

{
  "BiomeSpeciesMap": {
    "FOREST": ["ELF", "DRYAD", "SPRIGGAN", "TREANT", "WOLF", "STAG", "OWL", "FOX", "BEAR"],
    "SWAMP": ["TROLL", "HYDRA", "SERPENT", "GOBLIN", "NAGA", "WRAITH", "BOAR"],
    "MOUNTAIN": ["GIANT", "WYVERN", "GRIFFIN", "GOLEM", "TROLL", "ROC", "DRAGON"],
    "SNOWLAND": ["YETI", "WOLF", "DRAGON", "ELF", "WRAITH", "GIANT", "PHOENIX"],
    "GLACIER": ["YETI", "DRAGON", "WRAITH", "GIANT", "SERPENT"],
    "VOLCANIC_MOUNTAIN": ["DRAGON", "DRAKE", "ELEMENTAL", "GOLEM", "MANTICORE"],
    "FAE_REALM": ["ELF", "UNICORN", "DRYAD", "SPRIGGAN", "PHOENIX"],
    "UNDERGROUND": ["GOBLIN", "KOBOLD", "GOLEM", "MIMIC", "BASILISK", "SERPENT"]
  }
}

Then:

eligible_species = BiomeSpeciesMap[biome]
species_index = byte[3] % len(eligible_species)
species = eligible_species[species_index]

Then map species -> family.

Example:

{
  "SpeciesFamilyMap": {
    "ELF": "ELF",
    "DRYAD": "FAE",
    "SPRIGGAN": "FAE",
    "TREANT": "BEAST",
    "WOLF": "BEAST",
    "DRAGON": "DRAGONKIN",
    "DRAKE": "DRAGONKIN",
    "WYVERN": "DRAGONKIN",
    "GIANT": "GIANTKIN",
    "YETI": "GIANTKIN",
    "GOBLIN": "GOBLINKIN",
    "KOBOLD": "GOBLINKIN",
    "WRAITH": "UNDEAD",
    "ELEMENTAL": "ELEMENTAL",
    "GOLEM": "CONSTRUCT",
    "NAGA": "SERPENTKIN",
    "KRAKEN": "AQUATIC",
    "ROC": "AVIAN",
    "PHOENIX": "AVIAN"
  }
}
4.7 Subtype derivation

Subtype should be based on species + biome, not just species.

Example mapping:

{
  "SubtypeMap": {
    "ELF": {
      "FOREST": ["WOODLAND_ELF", "MOSS_ELF", "GROVE_ELF"],
      "SNOWLAND": ["SNOW_ELF", "FROST_ELF", "WHITEBARK_ELF"],
      "MOUNTAIN": ["CRAG_ELF", "STONE_ELF", "HIGHPEAK_ELF"],
      "FAE_REALM": ["MOON_ELF", "STAR_ELF", "VEIL_ELF"]
    },
    "DRAGON": {
      "MOUNTAIN": ["PEAK_DRAGON", "CRAG_DRAGON", "SKYFANG_DRAGON"],
      "GLACIER": ["ICE_DRAGON", "RIME_DRAGON", "GLACIAL_DRAGON"],
      "VOLCANIC_MOUNTAIN": ["MAGMA_DRAGON", "EMBER_DRAGON", "ASHEN_DRAGON"]
    },
    "WOLF": {
      "FOREST": ["WOOD_WOLF", "SHADE_WOLF", "FERN_WOLF"],
      "SNOWLAND": ["SNOW_WOLF", "BLIZZARD_WOLF", "FROSTFANG_WOLF"],
      "PLAINS": ["WINDRUNNER_WOLF", "DUST_WOLF", "PRAIRIE_WOLF"]
    },
    "GOLEM": {
      "MOUNTAIN": ["GRANITE_GOLEM", "BASALT_GOLEM", "SUMMIT_GOLEM"],
      "CRYSTAL_CAVES": ["QUARTZ_GOLEM", "AMETHYST_GOLEM", "PRISM_GOLEM"],
      "VOLCANIC_MOUNTAIN": ["OBSIDIAN_GOLEM", "LAVAHEART_GOLEM", "ASHFORGED_GOLEM"]
    }
  }
}

Selection:

eligible_subtypes = SubtypeMap[species][biome]
subtype_index = byte[4] % len(eligible_subtypes)
sub_type = eligible_subtypes[subtype_index]

If a biome-specific subtype list is missing, use fallback:

SubtypeMap[species]["DEFAULT"]
4.8 Element, temperament, size, variant

Each is just modular selection from controlled enums:

element = ElementType[byte[5] % len(ElementType)]
temperament = TemperamentType[byte[6] % len(TemperamentType)]
size = SizeType[byte[7] % len(SizeType)]
variant = VariantType[byte[8] % len(VariantType)]

You can later add weighting by rarity if you want.

Example:

Legendary gets more access to VOID, LIGHT, ARCANE

Uncommon favors NATURE, STONE, WATER

That can be done with rarity-filtered lists.

4.9 Name and title generation

Use templates.

Name template
<VariantStyledPrefix> + <SubtypeStyledName>

Examples:

Mossbound Grove Elf

Frostborn Ice Dragon

Thornclad Granite Golem

Title template
"The <Role> of the <Domain>"

Examples:

The Warden of Hollow Pines

The Herald of White Storms

The Keeper of the Obsidian Path

Select title fragments deterministically from lists using bytes 9, 21, 22.

4.10 Attribute generation

Use raw bytes, but bias them by rarity.

Base formula:

stat = 1 + (byte % 100)

But better is rarity-tier ranges.

Recommended stat ranges
{
  "StatRangesByRarity": {
    "UNCOMMON": { "min": 25, "max": 55 },
    "RARE": { "min": 40, "max": 70 },
    "EPIC": { "min": 55, "max": 85 },
    "LEGENDARY": { "min": 70, "max": 100 }
  }
}

Formula:

range_size = max - min + 1
stat = min + (byte % range_size)

Apply for:

power

defense

agility

wisdom

ferocity

magic

luck

This prevents weak legendaries and overpowered uncommons.

4.11 Presentation layer

For card art, you’ll want deterministic art-direction signals.

Use config arrays for:

primary_color

secondary_color

sigil

frame_style

Example:

{
  "PrimaryColors": ["forest-green", "ice-blue", "ember-red", "stone-gray", "void-purple", "gold", "swamp-olive"],
  "SecondaryColors": ["silver", "black", "white", "bronze", "navy", "crimson"],
  "Sigils": ["moon", "horn", "leaf", "claw", "eye", "crown", "flame", "wave", "rune"],
  "FrameStyles": ["thorned", "frosted", "obsidian", "vined", "runic", "celestial", "bone-carved"]
}

Then map with bytes 10–13.

This is very useful for your card design pipeline later.

5) Collision handling and registry spec

This is the important future-proof part.

5.1 What counts as a collision?

There are two layers:

Source collision

Same canonical ID appears again.
That is not a problem. It should return the same creature.

Creature signature collision

Different canonical IDs produce the exact same creature signature.

That may or may not be acceptable depending on your rules.

5.2 Recommended creature signature

Use a compact, meaningful signature:

<RARITY>|<BIOME>|<SPECIES>|<SUBTYPE>|<ELEMENT>|<SIZE>|<TEMPERAMENT>|<VARIANT>

Example:

EPIC|SWAMP|HYDRA|MIRE_HYDRA|POISON|HUGE|AGGRESSIVE|ROTROOT

This is the identity you check against a registry table.

5.3 Registry tables

You’ll probably want these conceptual tables:

SourceRegistry

Maps source identity to generated creature.

{
  "canonical_id": "UPC_A|036000291452|CAPS_AND_CAPES|v1",
  "creature_id": "CC-EPIC-SWAMP-HYDRA-8A4C91B2",
  "seed_hash_hex": "..."
}
CreatureRegistry

Maps signature to existing creature record.

{
  "creature_signature": "EPIC|SWAMP|HYDRA|MIRE_HYDRA|POISON|HUGE|AGGRESSIVE|ROTROOT",
  "creature_id": "CC-EPIC-SWAMP-HYDRA-8A4C91B2",
  "canonical_id": "UPC_A|036000291452|CAPS_AND_CAPES|v1"
}
5.4 Deterministic collision resolution

If signature already exists for a different canonical ID:

Reroll method

Append deterministic salt:

reroll_canonical = canonical_id + "|reroll|1"
seed_1 = SHA256(reroll_canonical)

Regenerate all fields.

If still collides:

canonical_id + "|reroll|2"

Continue until unique or until max attempts reached.

This is still deterministic, because the same source will always follow the same reroll path.

Rule

generation_iteration = 0 for first attempt

increment for each collision reroll

5.5 When to allow duplicates anyway

You may actually want controlled duplication at lower tiers.

For example:

Uncommon: duplicates allowed

Rare: low collision tolerance

Epic: strongly minimized

Legendary: must be unique

That’s a very collectible-friendly model.

Example policy:

{
  "CollisionPolicy": {
    "UNCOMMON": "ALLOW",
    "RARE": "ALLOW_IF_STATS_DIFFER",
    "EPIC": "REROLL_ON_SIGNATURE_MATCH",
    "LEGENDARY": "REROLL_ON_ANY_ARCHETYPE_MATCH"
  }
}

That gives your higher tiers more prestige.

6) Full generation spec in sequence

Here is the deterministic algorithm in exact order.

Step 1

Accept input:

{
  "code_type": "UPC_A",
  "raw_value": "036000291452",
  "namespace": "CAPS_AND_CAPES",
  "generator_version": "v1"
}
Step 2

Normalize by code type.

Step 3

Build canonical ID:

UPC_A|036000291452|CAPS_AND_CAPES|v1
Step 4

Check SourceRegistry:

if exists, return existing creature

if not, continue

Step 5

Generate seed:

seed = SHA256(canonical_id)
Step 6

Derive rarity from byte 0.

Step 7

Derive biome from byte 1.

Step 8

Get eligible species from biome map.

Step 9

Derive species from eligible list using byte 3.

Step 10

Map species to family.

Step 11

Derive subtype from SubtypeMap[species][biome] using byte 4.

Step 12

Derive element, temperament, size, variant.

Step 13

Derive presentation info:

colors

sigil

frame style

title

display name

Step 14

Derive stats using rarity-bounded ranges.

Step 15

Build creature signature.

Step 16

Check CreatureRegistry.

no collision: persist

collision with same canonical ID: return existing

collision with different canonical ID: reroll deterministically

Step 17

Persist to both registries.

7) Example generated object
{
  "schema_version": "1.0.0",
  "namespace": "CAPS_AND_CAPES",
  "source": {
    "code_type": "UPC_A",
    "raw_value": "036000291452",
    "normalized_value": "036000291452",
    "canonical_id": "UPC_A|036000291452|CAPS_AND_CAPES|v1",
    "normalization_ruleset_version": "1.0.0"
  },
  "identity": {
    "seed_hash_hex": "8a4c91b26d9f3f6d98d472d82314af7f6aa90f7a865682dc1e4cb5d0f511c30e",
    "generation_iteration": 0,
    "creature_id": "CC-RARE-FOREST-ELF-8A4C91B2",
    "creature_signature": "RARE|FOREST|ELF|WOODLAND_ELF|NATURE|MEDIUM|WISE|MOSSBOUND"
  },
  "generation": {
    "generator_version": "v1",
    "rarity_roll": 81,
    "selection_indices": {
      "biome_index": 0,
      "family_index": 0,
      "subtype_index": 1,
      "element_index": 0,
      "temperament_index": 0,
      "size_index": 1,
      "title_index": 4
    }
  },
  "classification": {
    "rarity": "RARE",
    "biome": "FOREST",
    "family": "ELF",
    "species": "ELF",
    "sub_type": "WOODLAND_ELF",
    "element": "NATURE",
    "temperament": "WISE",
    "size": "MEDIUM",
    "variant": "MOSSBOUND",
    "tags": [
      "forest",
      "elf",
      "nature",
      "wise",
      "rare"
    ]
  },
  "presentation": {
    "name": "Mossbound Woodland Elf",
    "title": "The Warden of Hollow Pines",
    "flavor_profile": {
      "primary_color": "forest-green",
      "secondary_color": "silver",
      "sigil": "leaf",
      "frame_style": "thorned"
    },
    "lore_seed": "Ancient guardian of hidden woodland paths and root-bound shrines."
  },
  "attributes": {
    "power": 57,
    "defense": 62,
    "agility": 69,
    "wisdom": 66,
    "ferocity": 45,
    "magic": 63,
    "luck": 54
  },
  "registry": {
    "collision_checked": true,
    "collision_resolved": false,
    "collision_resolution_mode": "NONE",
    "first_seen_at": "2026-03-06T19:00:00-08:00"
  }
}
8) Minimal config object for implementation

This is a more app-friendly config format:

{
  "generator_version": "v1",
  "namespace": "CAPS_AND_CAPES",
  "rarity_rules": {
    "UNCOMMON": [0, 74],
    "RARE": [75, 92],
    "EPIC": [93, 98],
    "LEGENDARY": [99, 99]
  },
  "stat_ranges": {
    "UNCOMMON": { "min": 25, "max": 55 },
    "RARE": { "min": 40, "max": 70 },
    "EPIC": { "min": 55, "max": 85 },
    "LEGENDARY": { "min": 70, "max": 100 }
  },
  "collision_policy": {
    "UNCOMMON": "ALLOW",
    "RARE": "ALLOW_IF_STATS_DIFFER",
    "EPIC": "REROLL_ON_SIGNATURE_MATCH",
    "LEGENDARY": "REROLL_ON_SIGNATURE_MATCH"
  },
  "max_rerolls": 25
}
9) Practical engineering recommendation

For your system, I’d suggest:

Start with these guarantees

same code type + same normalized value + same namespace + same version = same creature

UPC, EAN, QR never collide at source level because code type is part of canonical ID

rarity is deterministic and weighted

biomes constrain believable subtype generation

Epic and Legendary use registry-backed uniqueness rules

Do not overcomplicate v1 with

deep lore generation

too many stat formulas

dynamic cross-biome hybrids

QR URL normalization rules beyond trim/exact match

Get the identity and deterministic layer solid first.