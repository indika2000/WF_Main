# Testing — System Guide

## Overview

The WildernessFriends test suite covers 5 backend services with 245 tests total. Python services use **pytest** with async support; the Node.js gateway uses **Jest**. All tests run inside Docker containers via `docker-compose exec`, ensuring the test environment matches production.

### Design Principles

1. **No real external API calls** — Stripe, Firebase, AI providers, and inter-service HTTP calls are all mocked
2. **In-memory databases** — mongomock-motor replaces MongoDB, FakeRedis replaces Redis
3. **Shared conftest patterns** — every Python service follows the same fixture structure
4. **CI uses `.env.example`** — no secrets needed; everything is mocked

---

## Test Architecture

### Python Services (pytest)

All four Python services share an identical test architecture:

```
service-name/tests/
├── conftest.py          # Fixtures: test_db, test_client, auth headers, service-specific mocks
├── unit/                # Pure logic tests (no HTTP requests)
│   ├── test_models.py   # Pydantic model validation
│   ├── test_services.py # Business logic layer
│   └── ...              # Service-specific (test_storage.py, test_providers.py, etc.)
└── integration/         # Route/endpoint tests (httpx AsyncClient → FastAPI app)
    ├── test_*_routes.py # One file per route group
    └── ...
```

**Key configuration** (`services/pytest.ini`):
```ini
[pytest]
asyncio_mode = auto                        # No need for @pytest.mark.asyncio
asyncio_default_fixture_loop_scope = session  # Prevents event loop conflicts
log_cli = true
log_cli_level = WARNING
testpaths = tests
```

The `asyncio_mode = auto` setting means every `async def test_*` function is automatically treated as an async test — no decorators needed. The `session`-scoped event loop prevents the SSE event loop binding issue (see [Lesson #23](../01_LESSONS_LEARNED.md)).

### Node.js Gateway (Jest)

```
node-gateway/tests/
├── jest.config.js       # Config: 10s timeout, force exit, auto-mock cleanup
├── setup.js             # Sets env vars (JWT_SECRET, Firebase creds, service URLs)
├── helpers/
│   ├── mockFirebase.js  # Firebase Admin SDK mock functions
│   └── mockServices.js  # nock-based backend service mocks
├── unit/                # Pure function tests
│   ├── jwt.test.js      # Token signing and verification
│   └── responses.test.js # Response envelope formatting
└── integration/         # supertest-based route tests
    ├── auth.test.js     # Token exchange and verification
    ├── health.test.js   # Health check endpoints
    └── rateLimiter.test.js # Rate limiting behavior
```

**Jest config highlights** (`tests/jest.config.js`):
```javascript
module.exports = {
  testEnvironment: 'node',
  rootDir: '../',
  testMatch: ['<rootDir>/tests/**/*.test.js'],
  setupFilesAfterSetup: ['./tests/setup.js'],
  testTimeout: 10000,
  forceExit: true,
  clearMocks: true,
  resetMocks: true,
  restoreMocks: true,
};
```

`forceExit: true` is required because nock interceptors and open handles from supertest can prevent Jest from exiting naturally.

---

## Conftest Patterns (Python)

Every Python service conftest follows this exact structure:

### 1. Environment Variables First

```python
import os

# Set test environment variables BEFORE importing the app
os.environ["MONGODB_URI"] = "mongodb://localhost:27017/test_db"
os.environ["INTERNAL_API_KEY"] = "test-api-key"
os.environ["JWT_SECRET"] = "test-jwt-secret-for-testing"
os.environ["SERVICE_NAME"] = "service-test"
# ... service-specific vars ...
```

**This MUST come before any app imports.** Pydantic-settings reads environment variables at class definition time. If the app is imported first, config validation fails with missing required fields. See [Lesson #21](../01_LESSONS_LEARNED.md).

### 2. Test Database (mongomock-motor)

```python
from mongomock_motor import AsyncMongoMockClient

@pytest.fixture
async def test_db():
    """Provide a clean test MongoDB for each test."""
    client = AsyncMongoMockClient()
    db = client["test_db"]
    yield db
    client.close()
```

`mongomock_motor.AsyncMongoMockClient` is a drop-in replacement for `motor.AsyncIOMotorClient`. It provides an in-memory MongoDB that supports async operations. Each test gets a fresh database — no cleanup needed since the client is discarded.

### 3. Test HTTP Client

```python
from httpx import ASGITransport, AsyncClient
from app.main import app

@pytest.fixture
async def test_client(test_db):
    """Provide an async HTTP test client with injected test DB."""
    app.state.db = test_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
```

The `ASGITransport` adapter lets httpx call the FastAPI app directly (no network I/O). The test database is injected via `app.state.db`, which the app's lifespan normally sets from the real MongoDB connection.

### 4. Auth Header Fixtures

```python
import jwt as pyjwt

@pytest.fixture
def auth_headers():
    """Standard user JWT."""
    token = pyjwt.encode(
        {"uid": "test-user-123", "email": "test@example.com", "role": "user", "permissions": {}},
        "test-jwt-secret-for-testing",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def api_key_headers():
    """Service-to-service API key."""
    return {"X-Api-Key": "test-api-key"}

@pytest.fixture
def admin_headers():
    """Admin user JWT."""
    token = pyjwt.encode(
        {"uid": "admin-user", "email": "admin@example.com", "role": "admin", "permissions": {}},
        "test-jwt-secret-for-testing",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}
```

The JWT secret `"test-jwt-secret-for-testing"` matches the env var set at the top of conftest, which the app's `shared.python.auth` module reads for token verification. Three auth levels are provided: unauthenticated (no headers), user, and admin.

---

## Service-Specific Mock Patterns

### Commerce: FakeRedis with Per-Test Isolation

```python
import fakeredis.aioredis

@pytest.fixture
async def test_redis():
    server = fakeredis.FakeServer()
    r = fakeredis.aioredis.FakeRedis(decode_responses=True, server=server)
    yield r
    await r.close()

@pytest.fixture
async def test_client(test_db, test_redis):
    app.state.db = test_db
    app.state.redis = test_redis
    # ...
```

**Critical:** Each test must create a unique `FakeServer()`. Without it, FakeRedis instances share an implicit global server, and data from one test leaks into the next. This caused 11 phantom failures in cart/checkout tests before we added `FakeServer()` isolation. See [Lesson #22](../01_LESSONS_LEARNED.md).

### Commerce: Stripe Mocks (autouse)

```python
class MockObj:
    """Simulates Stripe's attribute-based object interface."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
    def __getitem__(self, key):
        return getattr(self, key)
    def get(self, key, default=None):
        return getattr(self, key, default)

@pytest.fixture(autouse=True)
def mock_stripe(monkeypatch):
    monkeypatch.setattr(stripe.Customer, "create",
        staticmethod(lambda **kw: MockObj(id="cus_test123")))
    monkeypatch.setattr(stripe.PaymentIntent, "create",
        staticmethod(lambda **kw: MockObj(
            id="pi_test123", client_secret="pi_test123_secret_xxx",
            status="requires_payment_method")))
    # ... all Stripe SDK methods mocked ...
```

The `autouse=True` ensures no Stripe API call ever reaches the real Stripe servers, even accidentally. The `MockObj` class mimics Stripe's response objects which use attribute access (e.g., `customer.id`) rather than dict access.

**Mocked Stripe methods:**
- `Customer.create`
- `PaymentIntent.create`, `PaymentIntent.retrieve`
- `PaymentMethod.retrieve`
- `EphemeralKey.create`
- `Subscription.create`, `Subscription.modify`, `Subscription.retrieve`

### LLM: Provider Factory Injection

```python
class MockTextProvider:
    name = "mock-text"
    model = "mock-model-v1"

    async def generate(self, messages, max_tokens=4096, temperature=0.7):
        return {"content": "Mock response", "tokens_used": 42, "finish_reason": "stop"}

    async def stream(self, messages, max_tokens=4096, temperature=0.7):
        for chunk in ["Mock ", "stream ", "response"]:
            yield chunk

class MockImageProvider:
    name = "mock-image"
    model = "mock-image-v1"

    async def generate(self, prompt, size="1024x1024", quality="standard", n=1):
        return [{"data": "bW9jayBpbWFnZSBkYXRh", "format": "png", "size": size}]

@pytest.fixture
async def test_client(test_db):
    app.state.db = test_db
    provider_factory._text_providers = {"mock-text": MockTextProvider()}
    provider_factory._image_providers = {"mock-image": MockImageProvider()}
    provider_factory._text_config = {"primary": "mock-text"}
    provider_factory._image_config = {"primary": "mock-image"}
    # ...
```

Mock providers are injected directly into the singleton `provider_factory` instance. The env var `LLM_CONFIG_PATH=/nonexistent/providers.yml` prevents the factory from loading real provider configs. Mock providers implement the same interface as real providers (Anthropic, OpenAI, Gemini).

### LLM: SSE Event Loop Reset

```python
import asyncio

@pytest.fixture(autouse=True)
def reset_sse_app_status():
    """Reset sse_starlette's AppStatus event to avoid event-loop binding issues."""
    try:
        from sse_starlette.sse import AppStatus
        AppStatus.should_exit_event = asyncio.Event()
    except (ImportError, AttributeError):
        pass
```

`sse_starlette` creates a module-level `asyncio.Event()` that binds to whichever event loop first accesses it. In tests, if a different event loop is used for subsequent tests, `RuntimeError: Event is bound to a different event loop` is raised. The autouse fixture replaces it with a fresh event before each test. See [Lesson #23](../01_LESSONS_LEARNED.md).

### Image: MockStorage Backend

```python
class MockStorage:
    """In-memory storage backend for testing."""
    def __init__(self):
        self._files = {}

    async def save(self, path, data):
        self._files[path] = data
        return path

    async def load(self, path):
        return self._files.get(path)

    async def delete(self, path):
        self._files.pop(path, None)

    async def exists(self, path):
        return path in self._files

    def get_url(self, path):
        return f"/images/file/{path}"

@pytest.fixture
async def test_client(test_db):
    app.state.db = test_db
    app.state.storage = MockStorage()
    # ...
```

The `MockStorage` replaces the `LocalStorage` filesystem backend. All file operations happen against an in-memory dict — no filesystem side effects during tests.

### Image: Test Image Generation

```python
from PIL import Image
import io

def create_test_image(width=100, height=100, format="PNG"):
    img = Image.new("RGB", (width, height), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format=format)
    buffer.seek(0)
    return buffer.getvalue()

@pytest.fixture
def test_image_data():
    return create_test_image()
```

Creates minimal valid PNG images for upload tests without needing real image files.

### Image: AsyncMock vs MagicMock for httpx Responses

```python
from unittest.mock import MagicMock, patch

# CORRECT — response.json() is synchronous
mock_response = MagicMock()
mock_response.status_code = 200
mock_response.json.return_value = {"success": True, "data": {...}}

# WRONG — AsyncMock makes .json() return a coroutine
mock_response = AsyncMock()  # Don't use this for httpx responses
```

httpx's `response.json()` is a synchronous method. `AsyncMock` would make it return a coroutine, causing `'coroutine' object has no attribute 'get'`. See [Lesson #30](../01_LESSONS_LEARNED.md).

### Gateway: Firebase Mock

```javascript
// helpers/mockFirebase.js
const admin = require('firebase-admin');

function mockFirebaseVerify() {
  jest.spyOn(admin.auth(), 'verifyIdToken').mockResolvedValue({
    uid: 'test-uid-123',
    email: 'test@example.com',
    email_verified: true,
  });
}

function mockFirebaseReject() {
  jest.spyOn(admin.auth(), 'verifyIdToken')
    .mockRejectedValue(new Error('Invalid token'));
}
```

### Gateway: nock-Based Service Mocks

```javascript
// helpers/mockServices.js
const nock = require('nock');

function mockPermissionsGet(userId, permissions = {}) {
  return nock('http://permissions:5003')
    .get(`/permissions/${userId}`)
    .reply(200, { success: true, data: { user_id: userId, permissions } });
}

function mockSubscriptionGet(userId, tier = 'free') {
  return nock('http://permissions:5003')
    .get(`/permissions/subscriptions/${userId}`)
    .reply(200, { success: true, data: { tier } });
}
```

**nock `.times(2)` for shared URLs:** The LLM and Chat services share `http://llm-service:5000`. Health check tests must use `.times(2)` on mocks for that URL since nock interceptors are consumed once by default. See [Lesson #31](../01_LESSONS_LEARNED.md).

---

## CI/CD Pipeline

### GitHub Actions Workflow

**File:** `.github/workflows/test.yml`

**Triggers:**
- Push to `main`
- Pull requests targeting `main`

**Pipeline Steps:**

```
1. Checkout code
2. Copy .env.example → .env (no real secrets)
3. Build all services with docker-compose (--build)
4. Wait for MongoDB readiness (polls up to 60 seconds)
5. Brief pause for service initialization (10 seconds)
6. Run Python tests: permissions → llm-service → image-service → commerce
7. Run Gateway tests: npm test
8. Teardown: docker-compose down -v (clean state)
```

**Key CI decisions:**

| Decision | Reason |
|----------|--------|
| Uses `.env.example` | No secrets in CI — all external calls are mocked |
| `down -v` in teardown | Clean state for next run — safe in CI, destructive in dev |
| 60-second MongoDB wait | Services fail with connection errors if DB isn't ready |
| 10-second initialization pause | Allows all 4 Python services to complete startup |
| `timeout-minutes: 15` | Prevents runaway builds; typical run is 3-5 minutes |

### What Must Be Mocked for CI

Since CI uses `.env.example` (placeholder keys), these external services MUST be mocked in all tests:

| External Service | Mocking Approach |
|------------------|------------------|
| Stripe API | `mock_stripe` autouse fixture (monkeypatch) |
| Firebase Admin | `mockFirebase.js` helper (jest.spyOn) |
| AI Providers (Anthropic, OpenAI, Gemini) | `MockTextProvider` / `MockImageProvider` injected into factory |
| Inter-service HTTP (Commerce → Permissions) | `unittest.mock.patch` on httpx calls |
| Filesystem storage | `MockStorage` in-memory dict |

---

## How to Add Tests for a New Service

### Python Service Test Setup

1. **Create test directories:**
   ```
   new-service/tests/
   ├── conftest.py
   ├── unit/
   │   └── test_models.py
   └── integration/
       └── test_routes.py
   ```

2. **Write conftest.py** — follow the standard pattern:
   ```python
   import os

   # ALL env vars BEFORE any app import
   os.environ["MONGODB_URI"] = "mongodb://localhost:27017/test_db"
   os.environ["INTERNAL_API_KEY"] = "test-api-key"
   os.environ["JWT_SECRET"] = "test-jwt-secret-for-testing"
   os.environ["SERVICE_NAME"] = "new-service-test"
   # ... service-specific env vars ...

   import pytest
   from httpx import ASGITransport, AsyncClient
   from mongomock_motor import AsyncMongoMockClient

   from app.main import app

   @pytest.fixture
   async def test_db():
       client = AsyncMongoMockClient()
       db = client["test_db"]
       yield db
       client.close()

   @pytest.fixture
   async def test_client(test_db):
       app.state.db = test_db
       transport = ASGITransport(app=app)
       async with AsyncClient(transport=transport, base_url="http://test") as client:
           yield client

   @pytest.fixture
   def api_key_headers():
       return {"X-Api-Key": "test-api-key"}

   @pytest.fixture
   def auth_headers():
       import jwt as pyjwt
       token = pyjwt.encode(
           {"uid": "test-user-123", "email": "test@example.com",
            "role": "user", "permissions": {}},
           "test-jwt-secret-for-testing", algorithm="HS256",
       )
       return {"Authorization": f"Bearer {token}"}

   @pytest.fixture
   def admin_headers():
       import jwt as pyjwt
       token = pyjwt.encode(
           {"uid": "admin-user", "email": "admin@example.com",
            "role": "admin", "permissions": {}},
           "test-jwt-secret-for-testing", algorithm="HS256",
       )
       return {"Authorization": f"Bearer {token}"}
   ```

3. **Add pytest.ini mount** in `docker-compose.dev.yml`:
   ```yaml
   volumes:
     - ./new-service/tests:/app/tests
     - ./pytest.ini:/app/pytest.ini
   ```

4. **Add to `run-tests.sh`** — append service name to `PYTHON_SERVICES`:
   ```bash
   PYTHON_SERVICES=("permissions" "llm-service" "image-service" "commerce" "new-service")
   ```

5. **Add to CI workflow** (`.github/workflows/test.yml`):
   ```yaml
   for svc in permissions llm-service image-service commerce new-service; do
   ```

6. **Add test dependencies** to `requirements.txt`:
   ```
   pytest>=8.0
   pytest-asyncio>=0.24
   httpx>=0.27
   mongomock-motor>=0.0.30
   ```
   Plus service-specific test deps (e.g., `fakeredis` for Redis, `Pillow` for images).

### Writing Tests

#### Unit Tests

Unit tests verify business logic without HTTP transport:

```python
# tests/unit/test_services.py
import pytest
from app.services.my_service import MyService

class TestMyService:
    async def test_create_item(self, test_db):
        service = MyService(test_db)
        result = await service.create({"name": "test"})
        assert result is not None
        assert result["name"] == "test"
```

#### Integration Tests

Integration tests verify the full request cycle through FastAPI:

```python
# tests/integration/test_routes.py
import pytest

class TestMyRoutes:
    async def test_create_item(self, test_client, auth_headers):
        response = await test_client.post(
            "/items/",
            json={"name": "test"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "test"

    async def test_requires_auth(self, test_client):
        response = await test_client.post("/items/", json={"name": "test"})
        assert response.status_code == 401
```

### Test Naming Conventions

| Pattern | Example |
|---------|---------|
| Positive case | `test_create_item` |
| Negative case | `test_create_item_duplicate_returns_409` |
| Auth required | `test_requires_auth`, `test_unauthorized_request` |
| Not found | `test_get_item_not_found` |
| Edge case | `test_update_item_zero_removes` |

---

## Test Dependencies

### Python (all services)

| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | ≥8.0 | Test framework |
| `pytest-asyncio` | ≥0.24 | Async test support |
| `httpx` | ≥0.27 | Async HTTP test client (ASGITransport) |
| `mongomock-motor` | ≥0.0.30 | In-memory async MongoDB mock |
| `PyJWT` | ≥2.8 | JWT token generation for auth fixtures |

### Service-Specific Python

| Package | Service | Purpose |
|---------|---------|---------|
| `fakeredis[aioredis]` | Commerce | In-memory async Redis mock |
| `Pillow` | Image | Test image generation |

### Node.js (Gateway)

| Package | Purpose |
|---------|---------|
| `jest` | Test framework |
| `supertest` | HTTP integration testing |
| `nock` | HTTP request mocking |

---

## Troubleshooting

### Tests Fail on Fresh Clone

```bash
# 1. Ensure containers are running
cd services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# 2. Wait for MongoDB
docker-compose exec -T mongodb mongosh --eval "db.runCommand({ping:1})" --quiet

# 3. Run tests
./run-tests.sh
```

### Tests Pass Individually but Fail Together

This is almost always a **state leak** between tests:
- **Redis:** Ensure `FakeServer()` per test (not shared)
- **MongoDB:** mongomock-motor creates fresh DBs per test by default — check if a fixture is reusing state
- **Module-level singletons:** Check if a factory or config object retains state (e.g., provider_factory)

### Import Errors at Test Collection Time

If pytest can't even collect tests:
1. Verify all env vars are set **at the top** of conftest.py, before any `from app...` import
2. Verify `PYTHONPATH=/app` is set in the Dockerfile
3. Verify the `shared/` directory is mounted in `docker-compose.dev.yml`

### SSE Streaming Tests Hang

If LLM streaming tests hang or timeout:
1. Verify `reset_sse_app_status` fixture exists and is `autouse=True`
2. Verify `asyncio_default_fixture_loop_scope = session` in `pytest.ini`
3. Check that `forceExit: true` is set in Jest config (gateway only)

---

## Cross-References

| Topic | Document |
|-------|----------|
| Quick commands | [QUICK_REFERENCE.md](QUICK_REFERENCE.md) |
| All gotchas | [01_LESSONS_LEARNED.md](../01_LESSONS_LEARNED.md) |
| Test-related gotchas | [01_LESSONS_LEARNED.md](../01_LESSONS_LEARNED.md) — items #21–31 |
| Master architecture | [00_MASTER_ARCHITECTURE.md](../00_MASTER_ARCHITECTURE.md) |
| Gateway test details | [gateway/SYSTEM_GUIDE.md](../gateway/SYSTEM_GUIDE.md) |
| Commerce test details | [commerce/SYSTEM_GUIDE.md](../commerce/SYSTEM_GUIDE.md) |
| LLM test details | [llm-service/SYSTEM_GUIDE.md](../llm-service/SYSTEM_GUIDE.md) |
| Image test details | [image-service/SYSTEM_GUIDE.md](../image-service/SYSTEM_GUIDE.md) |
