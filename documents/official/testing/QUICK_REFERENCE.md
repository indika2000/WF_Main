# Testing — Quick Reference

## Test Suite Summary

| Service | Unit Tests | Integration Tests | Total | Framework |
|---------|-----------|-------------------|-------|-----------|
| **Character** | 53 | 86 | **160** | pytest + mongomock-motor |
| **Permissions** | 26 | 20 | **46** | pytest + mongomock-motor |
| **Commerce** | 37 | 37 | **74** | pytest + mongomock-motor + FakeRedis |
| **LLM** | 35 | 24 | **59** | pytest + mongomock-motor |
| **Image** | 24 | 20 | **44** | pytest + mongomock-motor |
| **Gateway** | 11 | 11 | **22** | Jest + nock + supertest |
| **Total** | **186** | **198** | **405** | |

---

## Running Tests

All commands are executed from the `services/` directory with Docker containers running.

### Prerequisites

Start the full stack before running tests:
```bash
cd services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### Unified Test Runner

```bash
# Run ALL tests (all 5 services)
./run-tests.sh

# Unit tests only
./run-tests.sh --unit

# Integration tests only
./run-tests.sh --integration

# All tests with coverage report
./run-tests.sh --coverage

# Single service
./run-tests.sh --service character-service
./run-tests.sh --service permissions
./run-tests.sh --service commerce
./run-tests.sh --service llm-service
./run-tests.sh --service image-service
./run-tests.sh --service gateway
```

### Per-Service Commands (Manual)

#### Python Services (via docker-compose exec)

```bash
# Character — 160 tests
docker-compose exec -T character-service pytest tests/ -v --tb=short

# Permissions — 46 tests
docker-compose exec -T permissions pytest tests/ -v --tb=short

# Commerce — 74 tests
docker-compose exec -T commerce pytest tests/ -v --tb=short

# LLM — 59 tests
docker-compose exec -T llm-service pytest tests/ -v --tb=short

# Image — 44 tests
docker-compose exec -T image-service pytest tests/ -v --tb=short
```

#### Unit or Integration Only (Python)

```bash
# Unit tests only
docker-compose exec -T permissions pytest tests/unit/ -v

# Integration tests only
docker-compose exec -T permissions pytest tests/integration/ -v
```

#### Coverage Report (Python)

```bash
docker-compose exec -T commerce pytest tests/ -v --cov=app --cov-report=term-missing
```

#### Gateway (Node.js)

```bash
# All gateway tests — 22 tests
docker-compose exec -T gateway npm test

# Unit only
docker-compose exec -T gateway npm run test:unit

# Integration only
docker-compose exec -T gateway npm run test:integration
```

### PowerShell One-Liner (Windows)

```powershell
# Run all Python services + gateway in sequence
@("character-service","permissions","llm-service","image-service","commerce") | ForEach-Object {
  Write-Host "`n=== Testing $_ ===" -ForegroundColor Yellow
  docker-compose exec -T $_ pytest tests/ -v --tb=short
}
Write-Host "`n=== Testing gateway ===" -ForegroundColor Yellow
docker-compose exec -T gateway npm test
```

---

## Test File Locations

```
services/
├── pytest.ini                           # Shared pytest config (asyncio_mode=auto)
├── run-tests.sh                         # Unified test runner script
│
├── character-service/tests/
│   ├── conftest.py                      # MongoDB mock, auth, config fixtures (v1, v2, cyber)
│   ├── fixtures/
│   │   ├── generation_v2_test.yml       # Ocean-themed season test config
│   │   └── generation_cyber_test.yml    # CyberFriends world test config
│   ├── unit/
│   │   ├── test_config.py              # 25 tests — loading, validation, weights, templates
│   │   ├── test_generator.py           # 14 tests — determinism, rarity, constraints
│   │   └── test_normalisation.py       # 14 tests — barcode format validation
│   └── integration/
│       ├── test_generate_routes.py     # 16 tests — API endpoints
│       ├── test_registry.py            # 11 tests — DB persistence, collisions
│       ├── test_barcode_stress.py      # 8 tests — 500-barcode stress
│       ├── test_1000_barcodes.py       # 16 tests — 1000-barcode season tests
│       └── test_cross_world.py         # 35 tests — 1000-barcode cross-world
│
├── permissions-service/tests/
│   ├── conftest.py                      # MongoDB mock, auth fixtures
│   ├── unit/
│   │   ├── test_models.py              # 12 tests — Pydantic models, tiers
│   │   └── test_services.py            # 14 tests — business logic
│   └── integration/
│       ├── test_permissions_routes.py   # 8 tests — CRUD + check
│       ├── test_subscription_routes.py  # 6 tests — tier sync
│       └── test_usage_routes.py         # 6 tests — metering
│
├── commerce-service/tests/
│   ├── conftest.py                      # MongoDB + Redis mocks, Stripe mocks
│   ├── unit/
│   │   ├── test_models.py              # 12 tests — cart, order, profile models
│   │   ├── test_cart_service.py        # 12 tests — Redis cart operations
│   │   ├── test_checkout_service.py    # 7 tests — payment + order creation
│   │   └── test_webhook_service.py     # 6 tests — Stripe event handling
│   └── integration/
│       ├── test_cart_routes.py          # 8 tests — cart API
│       ├── test_checkout_routes.py      # 7 tests — checkout flow API
│       ├── test_order_routes.py         # 12 tests — orders + profile + webhooks
│       └── test_subscription_routes.py  # 10 tests — subscription CRUD
│
├── llm-service/tests/
│   ├── conftest.py                      # MongoDB mock, provider injection, SSE reset
│   ├── unit/
│   │   ├── test_models.py              # 10 tests — text/image/chat models
│   │   ├── test_providers.py           # 11 tests — factory + fallback
│   │   └── test_services.py            # 14 tests — generation + chat logic
│   └── integration/
│       ├── test_chat_routes.py          # 11 tests — conversation API
│       ├── test_generate_routes.py      # 8 tests — text/image generation API
│       └── test_provider_routes.py      # 5 tests — provider status API
│
├── image-service/tests/
│   ├── conftest.py                      # MongoDB mock, MockStorage, test images
│   ├── unit/
│   │   ├── test_models.py              # 8 tests — image models, presets
│   │   ├── test_processor.py           # 10 tests — image processing
│   │   └── test_storage.py             # 6 tests — storage backend
│   └── integration/
│       ├── test_image_routes.py         # 12 tests — upload/retrieve/delete
│       ├── test_generate_routes.py      # 3 tests — AI image generation
│       └── test_user_image_routes.py    # 5 tests — user image listing
│
└── node-gateway/
    ├── tests/
    │   ├── jest.config.js               # Jest config (timeout: 10s, force exit)
    │   ├── setup.js                     # Environment variables
    │   ├── helpers/
    │   │   ├── mockFirebase.js          # Firebase Admin SDK mock
    │   │   └── mockServices.js          # nock-based service mocks
    │   ├── unit/
    │   │   ├── jwt.test.js              # 6 tests — sign/verify/expiry
    │   │   └── responses.test.js        # 5 tests — response envelope
    │   └── integration/
    │       ├── auth.test.js             # 6 tests — token exchange + verify
    │       ├── health.test.js           # 3 tests — health endpoints
    │       └── rateLimiter.test.js      # 2 tests — rate limiting
    └── package.json                     # npm scripts: test, test:unit, test:integration
```

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: No module named 'app'` | Container not running or PYTHONPATH not set | `docker-compose up -d` and check Dockerfile has `ENV PYTHONPATH=/app` |
| `Connection refused` in tests | MongoDB/Redis not ready | Wait for containers: `docker-compose ps` should show "Up" |
| `RuntimeError: Event is bound to a different event loop` | SSE AppStatus in LLM tests | `reset_sse_app_status` autouse fixture resets it — verify conftest |
| `DuplicateKeyError` in commerce tests | Shared FakeRedis state | Ensure `test_redis` fixture creates unique `FakeServer()` per test |
| Cart tests have phantom items | FakeRedis state leak | Same fix — unique `FakeServer()` per test |
| `'coroutine' object has no attribute 'get'` | `AsyncMock` used for synchronous `.json()` | Use `MagicMock` for httpx response objects |
| Nock `RequestError` in health tests | Mock consumed by first request | Add `.times(2)` for shared service URLs (llm/chat) |
| `pydantic ValidationError` on import | Env vars not set before app import | Set `os.environ[...]` at top of conftest before any app imports |

---

## Cross-References

| Topic | Document |
|-------|----------|
| Gotchas affecting tests | [01_LESSONS_LEARNED.md](../01_LESSONS_LEARNED.md) — items #21–31 |
| Test architecture details | [SYSTEM_GUIDE.md](SYSTEM_GUIDE.md) |
| CI/CD pipeline | [SYSTEM_GUIDE.md](SYSTEM_GUIDE.md#cicd-pipeline) |
| Per-service test details | Each service's [SYSTEM_GUIDE.md](../gateway/SYSTEM_GUIDE.md) |
