# Character Service — Quick Reference

## Service Details

| Property | Value |
|----------|-------|
| **Port** | 5002 |
| **Framework** | Python 3.12 + FastAPI |
| **Database** | MongoDB 7.0 |
| **Config** | YAML-based (`GENERATION_CONFIG_PATH` env var) |
| **Auth** | JWT (via gateway) + API key (service-to-service) |
| **Tests** | 160 (unit + integration), pytest |

---

## Running the Service

```bash
# With Docker (full stack)
cd services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Local development
cd services/character-service
PYTHONPATH="../:." GENERATION_CONFIG_PATH=config/generation_v1.yml \
  uvicorn app.main:app --reload --port 5002
```

---

## Running Tests

```bash
# All 160 tests
cd services/character-service
PYTHONPATH="../:." python -m pytest tests/ -v --tb=short

# Unit tests only (fast — config, generator, normalisation)
PYTHONPATH="../:." python -m pytest tests/unit/ -v

# Integration tests only (1000-barcode suites, API routes, registry)
PYTHONPATH="../:." python -m pytest tests/integration/ -v

# Specific test file
PYTHONPATH="../:." python -m pytest tests/integration/test_cross_world.py -v

# Via unified runner (Docker)
cd services
./run-tests.sh --service character-service
```

---

## Test Suite Breakdown

| File | Tests | What it validates |
|------|-------|------------------|
| `unit/test_config.py` | 25 | Config loading, validation, biome weights, world templates |
| `unit/test_generator.py` | 14 | Determinism, rarity, constraints, claimed variants |
| `unit/test_normalisation.py` | 14 | Barcode format validation (UPC-A, EAN-13, QR) |
| `integration/test_generate_routes.py` | 16 | API endpoints, auth, idempotency |
| `integration/test_registry.py` | 11 | DB persistence, collisions, supply caps |
| `integration/test_barcode_stress.py` | 8 | 500-barcode stress tests |
| `integration/test_1000_barcodes.py` | 16 | 1000-barcode season tests (v1 vs v2) |
| `integration/test_cross_world.py` | 35 | 1000-barcode cross-world tests (WF vs CF) |
| **Total** | **160** | |

### Cross-World Tests (test_cross_world.py) — Detail

| Class | Tests | Coverage |
|-------|-------|----------|
| `TestCyberConfigValidation` | 14 | Config loads, counts, content differs from v1 |
| `TestCyberDeterminism1000` | 1 | 1000 barcodes deterministic in cyber world |
| `TestCyberUniqueness1000` | 1 | ≥99% unique IDs across 1000 barcodes |
| `TestWorldIsolation` | 4 | Same barcodes → different creatures, zero ID overlap, prefix/title differ |
| `TestCyberBiomeSpeciesConstraints1000` | 2 | Species valid for biome, subtypes valid |
| `TestCyberRarityDistribution1000` | 1 | Rarity proportions match weights |
| `TestCyberStatRangeCompliance1000` | 1 | All stats within rarity bounds |
| `TestCyberClaimedVariants1000` | 3 | All COMMON, differ from originals, deterministic |
| `TestCyberContentVerification` | 5 | Cyber biomes/species/elements/IDs/prefixes |
| `TestTemplateFlexibility` | 3 | Default templates, custom templates |

---

## Config Files

| File | Purpose | Location |
|------|---------|----------|
| `generation_v1.yml` | Production config (WildernessFriends Season 1) | `config/` |
| `generation_v2_test.yml` | Test config for ocean-themed season | `tests/fixtures/` |
| `generation_cyber_test.yml` | Test config for CyberFriends world | `tests/fixtures/` |

---

## Quick: Create a New Season

```yaml
# Copy generation_v1.yml, then modify:
version: "v2"                    # ← Change version
# namespace stays the same

biome_weights:                    # ← Add theme bias (optional)
  OCEAN: 5
  DEEP_OCEAN: 5
  CORAL_REEF: 5
  # Unlisted biomes default to weight 1
```

**What changes:** Every creature generated is different (hash isolation). Biome distribution can be themed.
**What stays:** Same species, biomes, elements, subtypes, stat ranges.

---

## Quick: Create a New World

```yaml
version: "c1"                    # Unique version
namespace: "CYBER_FRIENDS"       # Unique namespace
id_prefix: "CF"                  # Unique ID prefix
name_template: "{variant} {sub_type}"
title_template: "{role} of {domain}"

biomes:                           # Completely different biomes
  - NEON_DISTRICT
  - ORBITAL_STATION
  - CYBERSPACE

species:                          # Completely different species
  - { id: ANDROID, family: ANDROID }
  - { id: BATTLE_MECH, family: MECH }

# ... full config with biome_species_map, subtype_map, elements, etc.
```

**Validation:** The `GenerationConfig` class auto-validates all constraints (every biome has species, every species in at least one biome, every species has subtypes, etc.) and raises `ValueError` with descriptive messages.

---

## Key Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GENERATION_CONFIG_PATH` | Path to generation YAML | `config/generation_v1.yml` |
| `MONGODB_URI` | MongoDB connection string | `mongodb://mongo:27017/wilderness_friends` |
| `INTERNAL_API_KEY` | Service-to-service auth key | `your-api-key` |
| `JWT_SECRET` | JWT verification secret | `your-jwt-secret` |
| `SERVICE_NAME` | Service identifier | `character-service` |

---

## API Quick Reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/generate` | JWT | Generate creature from barcode |
| `GET` | `/creatures/{id}` | JWT | Get creature by ID |
| `GET` | `/collection` | JWT | Get user's collection (paginated) |
| `GET` | `/supply/status` | JWT | Supply counts vs caps |
| `GET` | `/health` | None | Basic health check |
| `GET` | `/health/detailed` | None | Detailed health with DB status |
