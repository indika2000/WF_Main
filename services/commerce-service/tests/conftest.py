import os

# Set test environment variables before importing the app
os.environ["MONGODB_URI"] = "mongodb://localhost:27017/test_db"
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["INTERNAL_API_KEY"] = "test-api-key"
os.environ["JWT_SECRET"] = "test-jwt-secret-for-testing"
os.environ["SERVICE_NAME"] = "commerce-test"
os.environ["STRIPE_SECRET_KEY"] = "sk_test_fake"
os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test_fake"
os.environ["STRIPE_PRICE_PREMIUM"] = "price_premium_test"
os.environ["STRIPE_PRICE_ULTRA"] = "price_ultra_test"

import stripe
import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient
import fakeredis.aioredis

from app.main import app


# ── Mock Objects ─────────────────────────────────────────────────────────────


class MockObj:
    """Simple mock object that returns attributes from kwargs."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)


# ── Database Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
async def test_db():
    """Provide a clean test MongoDB for each test."""
    client = AsyncMongoMockClient()
    db = client["test_db"]
    yield db
    client.close()


@pytest.fixture
async def test_redis():
    """Provide a clean test Redis for each test."""
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield r
    await r.aclose()


@pytest.fixture
async def test_client(test_db, test_redis):
    """Provide an async HTTP test client with injected test DB and Redis."""
    app.state.db = test_db
    app.state.redis = test_redis
    stripe.api_key = "sk_test_fake"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ── Auth Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def api_key_headers():
    """Provide API key headers for service-to-service testing."""
    return {"X-Api-Key": "test-api-key"}


@pytest.fixture
def auth_headers():
    """Provide valid JWT auth headers for testing."""
    token = pyjwt.encode(
        {
            "uid": "test-user-123",
            "email": "test@example.com",
            "role": "user",
            "permissions": {},
        },
        "test-jwt-secret-for-testing",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers():
    """Provide admin JWT auth headers for testing."""
    token = pyjwt.encode(
        {
            "uid": "admin-user",
            "email": "admin@example.com",
            "role": "admin",
            "permissions": {},
        },
        "test-jwt-secret-for-testing",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


# ── Stripe Mocks ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def mock_stripe(monkeypatch):
    """Mock all Stripe API calls to prevent real API calls in tests."""
    monkeypatch.setattr(
        stripe.Customer,
        "create",
        staticmethod(lambda **kw: MockObj(id="cus_test123")),
    )
    monkeypatch.setattr(
        stripe.PaymentIntent,
        "create",
        staticmethod(
            lambda **kw: MockObj(
                id="pi_test123",
                client_secret="pi_test123_secret_xxx",
                status="requires_payment_method",
            )
        ),
    )
    monkeypatch.setattr(
        stripe.PaymentIntent,
        "retrieve",
        staticmethod(
            lambda pid, **kw: MockObj(
                id=pid,
                status="succeeded",
                payment_method="pm_test123",
            )
        ),
    )
    monkeypatch.setattr(
        stripe.PaymentMethod,
        "retrieve",
        staticmethod(
            lambda pmid, **kw: MockObj(
                card=MockObj(brand="visa", last4="4242")
            )
        ),
    )
    monkeypatch.setattr(
        stripe.EphemeralKey,
        "create",
        staticmethod(lambda **kw: MockObj(secret="ek_test_secret")),
    )
    monkeypatch.setattr(
        stripe.Subscription,
        "create",
        staticmethod(
            lambda **kw: MockObj(
                id="sub_test123",
                status="incomplete",
                latest_invoice=MockObj(
                    payment_intent=MockObj(client_secret="pi_sub_secret")
                ),
            )
        ),
    )
    monkeypatch.setattr(
        stripe.Subscription,
        "modify",
        staticmethod(lambda sid, **kw: MockObj(id=sid, status="active")),
    )
    monkeypatch.setattr(
        stripe.Subscription,
        "retrieve",
        staticmethod(
            lambda sid, **kw: MockObj(
                id=sid,
                items={"data": [{"id": "si_item_test"}]},
            )
        ),
    )
