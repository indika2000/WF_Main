# Testing Strategy - Planning Document

## 1. Overview

Testing is built into the foundation from day one. Every service ships with unit and integration tests. Tests run inside Docker containers to match production parity.

## 2. Test Pyramid

```
         ╱╲
        ╱  ╲          Integration Tests
       ╱    ╲         (API endpoints, service interactions, DB)
      ╱──────╲
     ╱        ╲
    ╱          ╲       Unit Tests
   ╱            ╲      (Business logic, validators, helpers)
  ╱──────────────╲
```

**Unit tests** — fast, isolated, mock external dependencies. Test pure logic.
**Integration tests** — use real MongoDB/Redis (in Docker), test full request/response cycles.

## 3. Testing Stack

| Service Type | Framework | Runner | Assertion | Mocking |
|-------------|-----------|--------|-----------|---------|
| Python (FastAPI) | pytest | pytest | pytest assert | unittest.mock + pytest-mock |
| Python (HTTP) | httpx | pytest | pytest assert | respx (HTTP mocking) |
| Node.js (Express) | Jest | jest | expect | jest.mock |
| Node.js (HTTP) | supertest | jest | expect | nock |

## 4. Python Service Test Structure

Each FastAPI service follows the same test layout:

```
service/
├── app/
│   ├── main.py
│   ├── models/
│   ├── routes/
│   ├── services/
│   └── database.py
└── tests/
    ├── conftest.py              # Shared fixtures (test client, test DB, mocks)
    ├── unit/
    │   ├── test_models.py       # Pydantic model validation
    │   ├── test_services.py     # Business logic (DB mocked)
    │   └── test_utils.py        # Helper functions
    └── integration/
        ├── test_routes.py       # Full API endpoint tests
        ├── test_database.py     # DB operations with test MongoDB
        └── test_auth.py         # Auth middleware tests
```

### 4.1 Shared Fixtures (conftest.py)

```python
import pytest
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient
from app.main import app

@pytest.fixture
async def test_db():
    """Provide a clean test MongoDB for each test."""
    client = AsyncMongoMockClient()
    db = client["test_db"]
    yield db
    client.close()

@pytest.fixture
async def test_client(test_db):
    """Provide an async HTTP test client with injected test DB."""
    app.state.db = test_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

@pytest.fixture
def auth_headers():
    """Provide valid JWT auth headers for testing."""
    return {"Authorization": "Bearer test-jwt-token"}

@pytest.fixture
def api_key_headers():
    """Provide API key headers for service-to-service testing."""
    return {"X-Api-Key": "test-api-key"}
```

### 4.2 Unit Test Example

```python
# tests/unit/test_services.py
import pytest
from app.services.permissions import PermissionsService
from app.models.permissions import UserPermissions

class TestPermissionsService:
    def test_default_permissions_for_new_user(self):
        perms = PermissionsService.create_default_permissions("user123")
        assert perms.role == "user"
        assert perms.is_premium is False
        assert perms.permissions["ad_free"] is False
        assert perms.permissions["ai_text_generation"] is False

    def test_sync_permissions_to_premium_tier(self):
        perms = PermissionsService.create_default_permissions("user123")
        updated = PermissionsService.sync_to_tier(perms, "premium")
        assert updated.is_premium is True
        assert updated.permissions["ad_free"] is True
        assert updated.permissions["ai_image_generation"] is True

    def test_feature_usage_check_within_limit(self):
        usage = FeatureUsage(user_id="u1", feature="ai_text", used=5, limit=10, bonus=0)
        result = PermissionsService.check_usage(usage)
        assert result["allowed"] is True
        assert result["remaining"] == 5

    def test_feature_usage_check_at_limit(self):
        usage = FeatureUsage(user_id="u1", feature="ai_text", used=10, limit=10, bonus=0)
        result = PermissionsService.check_usage(usage)
        assert result["allowed"] is False
        assert result["remaining"] == 0

    def test_feature_usage_unlimited(self):
        usage = FeatureUsage(user_id="u1", feature="ai_text", used=9999, limit=-1, bonus=0)
        result = PermissionsService.check_usage(usage)
        assert result["allowed"] is True
```

### 4.3 Integration Test Example

```python
# tests/integration/test_routes.py
import pytest

class TestPermissionsRoutes:
    @pytest.mark.asyncio
    async def test_create_permissions(self, test_client, auth_headers):
        response = await test_client.post(
            "/permissions/user123",
            headers=auth_headers,
            json={"email": "test@example.com"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["role"] == "user"
        assert data["data"]["permissions"]["ad_free"] is False

    @pytest.mark.asyncio
    async def test_get_permissions(self, test_client, auth_headers):
        # Create first
        await test_client.post("/permissions/user123", headers=auth_headers, json={})
        # Get
        response = await test_client.get("/permissions/user123", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["data"]["user_id"] == "user123"

    @pytest.mark.asyncio
    async def test_check_permission_denied(self, test_client, auth_headers):
        await test_client.post("/permissions/user123", headers=auth_headers, json={})
        response = await test_client.get(
            "/permissions/user123/check/ai_image_generation",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["data"]["allowed"] is False

    @pytest.mark.asyncio
    async def test_unauthorized_request(self, test_client):
        response = await test_client.get("/permissions/user123")
        assert response.status_code == 401
```

## 5. Node.js Gateway Test Structure

```
node-gateway/
└── tests/
    ├── setup.js                  # Jest global setup
    ├── helpers/
    │   ├── mockFirebase.js       # Mock Firebase Admin SDK
    │   └── mockServices.js       # Mock backend service responses
    ├── unit/
    │   ├── jwt.test.js           # JWT sign/verify
    │   ├── responses.test.js     # Response formatter
    │   └── config.test.js        # Config loading
    └── integration/
        ├── auth.test.js          # Auth flow end-to-end
        ├── proxy.test.js         # Service proxying
        ├── health.test.js        # Health endpoints
        └── rateLimiter.test.js   # Rate limiting behavior
```

### 5.1 Unit Test Example

```javascript
// tests/unit/jwt.test.js
const { signToken, verifyToken } = require('../../src/utils/jwt');

describe('JWT Utils', () => {
  const payload = { uid: 'user123', email: 'test@example.com', role: 'user' };

  test('signs and verifies a valid token', () => {
    const token = signToken(payload);
    const decoded = verifyToken(token);
    expect(decoded.uid).toBe('user123');
    expect(decoded.email).toBe('test@example.com');
  });

  test('rejects expired token', () => {
    const token = signToken(payload, '0s'); // Immediate expiry
    expect(() => verifyToken(token)).toThrow('jwt expired');
  });

  test('rejects tampered token', () => {
    const token = signToken(payload) + 'tampered';
    expect(() => verifyToken(token)).toThrow();
  });
});
```

### 5.2 Integration Test Example

```javascript
// tests/integration/auth.test.js
const request = require('supertest');
const app = require('../../src/app');
const { mockFirebaseVerify } = require('../helpers/mockFirebase');

describe('POST /api/auth/token', () => {
  beforeEach(() => {
    mockFirebaseVerify({ uid: 'user123', email: 'test@example.com' });
  });

  test('exchanges Firebase token for internal JWT', async () => {
    const res = await request(app)
      .post('/api/auth/token')
      .set('Authorization', 'Bearer valid-firebase-token')
      .expect(200);

    expect(res.body.success).toBe(true);
    expect(res.body.data.token).toBeDefined();
    expect(res.body.data.user.uid).toBe('user123');
  });

  test('rejects missing auth header', async () => {
    const res = await request(app)
      .post('/api/auth/token')
      .expect(401);

    expect(res.body.success).toBe(false);
    expect(res.body.error_code).toBe('AUTH_REQUIRED');
  });
});
```

## 6. Running Tests

### 6.1 Inside Docker (Recommended)

```bash
# Run all tests for a specific service
docker-compose exec permissions pytest -v

# Run only unit tests
docker-compose exec permissions pytest tests/unit/ -v

# Run only integration tests
docker-compose exec permissions pytest tests/integration/ -v

# Run with coverage
docker-compose exec permissions pytest --cov=app --cov-report=term-missing

# Run Node gateway tests
docker-compose exec gateway npm test

# Run gateway tests with coverage
docker-compose exec gateway npm test -- --coverage
```

### 6.2 Run All Service Tests

```bash
# Script: services/run-tests.sh
#!/bin/bash
set -e

echo "=== Running Permissions Service Tests ==="
docker-compose exec -T permissions pytest -v --tb=short

echo "=== Running Commerce Service Tests ==="
docker-compose exec -T commerce pytest -v --tb=short

echo "=== Running Image Service Tests ==="
docker-compose exec -T image-service pytest -v --tb=short

echo "=== Running LLM Service Tests ==="
docker-compose exec -T llm-service pytest -v --tb=short

echo "=== Running Gateway Tests ==="
docker-compose exec -T gateway npm test

echo "=== All tests passed ==="
```

## 7. Test Database Strategy

- **MongoDB**: Use `mongomock-motor` for unit tests (in-memory mock). Use dedicated test database in Docker MongoDB for integration tests.
- **Redis**: Use `fakeredis` for unit tests. Use separate Redis DB index (e.g., DB 1) for integration tests.
- **Cleanup**: Each test gets a clean database state. Use fixtures that drop/create collections.

## 8. Mocking External Services

### 8.1 Service-to-Service Calls

When a service calls another (e.g., Commerce → Permissions), mock the HTTP call:

```python
# Python: using respx
@pytest.fixture
def mock_permissions_service(respx_mock):
    respx_mock.get("http://permissions:5003/permissions/user123").mock(
        return_value=Response(200, json={
            "success": True,
            "data": {"user_id": "user123", "permissions": {"ai_text_generation": True}}
        })
    )
```

### 8.2 Stripe API

```python
# Use stripe-mock or mock at HTTP level
@pytest.fixture
def mock_stripe(monkeypatch):
    monkeypatch.setattr("stripe.Customer.create", lambda **kwargs: {
        "id": "cus_test123"
    })
    monkeypatch.setattr("stripe.PaymentIntent.create", lambda **kwargs: {
        "id": "pi_test123",
        "client_secret": "pi_test123_secret_test"
    })
```

### 8.3 LLM Providers

```python
# Mock at the provider level
@pytest.fixture
def mock_anthropic(monkeypatch):
    async def mock_generate(self, messages, config):
        return TextResult(
            content="This is a mock response.",
            provider="anthropic",
            model="claude-sonnet-4",
            tokens_used=10,
            finish_reason="stop"
        )
    monkeypatch.setattr(AnthropicTextProvider, "generate", mock_generate)
```

## 9. Test Environment Variables

```env
# tests/.env.test
NODE_ENV=test
MONGODB_URI=mongodb://localhost:27017/test_db
REDIS_URL=redis://localhost:6379/1
JWT_SECRET=test-secret-key
INTERNAL_API_KEY=test-api-key
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_test_...
ANTHROPIC_API_KEY=test-key
OPENAI_API_KEY=test-key
GOOGLE_API_KEY=test-key
```

## 10. Coverage Targets

| Service | Target | Critical Paths |
|---------|--------|---------------|
| Permissions | 80%+ | Permission checks, usage metering, tier sync |
| Commerce | 80%+ | Cart operations, checkout flow, webhook handling |
| Image | 75%+ | Upload validation, processing, serving |
| LLM | 75%+ | Provider factory, fallback chain, streaming |
| Gateway | 80%+ | Auth middleware, JWT, proxy routing |

## 11. CI/CD Integration (Future)

When GitHub Actions is set up:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Start services
        run: docker-compose -f docker-compose.yml -f docker-compose.test.yml up -d
      - name: Wait for services
        run: ./scripts/wait-for-services.sh
      - name: Run all tests
        run: ./services/run-tests.sh
      - name: Upload coverage
        uses: codecov/codecov-action@v4
```

## 12. Test Naming Conventions

- **Test files**: `test_{module}.py` (Python), `{module}.test.js` (Node)
- **Test classes**: `TestClassName` (Python)
- **Test functions**: `test_descriptive_name` (Python), `test descriptive name` (Node)
- **Describe blocks**: `describe('Module/Route', () => {})` (Node)

Pattern: `test_{action}_{scenario}_{expected_result}`

Examples:
- `test_create_permissions_for_new_user_returns_defaults`
- `test_check_usage_at_limit_returns_denied`
- `test_checkout_with_empty_cart_returns_400`
