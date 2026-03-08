import os

# Set test environment variables before importing the app
os.environ["MONGODB_URI"] = "mongodb://localhost:27017/test_db"
os.environ["INTERNAL_API_KEY"] = "test-api-key"
os.environ["JWT_SECRET"] = "test-jwt-secret-for-testing"
os.environ["SERVICE_NAME"] = "character-test"
os.environ["GENERATION_CONFIG_PATH"] = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "config", "generation_v1.yml"
)

import yaml
import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.main import app
from app.services.config_loader import GenerationConfig, load_config


# ── Database Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
async def test_db():
    """Provide a clean test MongoDB for each test."""
    client = AsyncMongoMockClient()
    db = client["test_db"]
    # Create indexes that mirror init_indexes() for constraint enforcement
    await db.source_registry.create_index("canonical_id", unique=True)
    await db.user_collections.create_index(
        [("user_id", 1), ("creature_id", 1)], unique=True
    )
    await db.creatures.create_index("identity.creature_id", unique=True)
    await db.supply_counters.create_index(
        [("counter_key", 1), ("season", 1)], unique=True
    )
    yield db
    client.close()


@pytest.fixture
async def test_client(test_db):
    """Provide an async HTTP test client with injected test DB."""
    app.state.db = test_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ── Config Fixture ───────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def load_generation_config():
    """Ensure generation config is loaded for every test."""
    config_path = os.environ["GENERATION_CONFIG_PATH"]
    load_config(config_path)


# ── v2 Config Fixture ───────────────────────────────────────────────────────


@pytest.fixture
def v2_config():
    """Load v2 test config as a standalone GenerationConfig (no singleton mutation)."""
    v2_path = os.path.join(os.path.dirname(__file__), "fixtures", "generation_v2_test.yml")
    with open(v2_path) as f:
        data = yaml.safe_load(f)
    return GenerationConfig(data)


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
def auth_headers_user2():
    """Provide valid JWT auth headers for a second test user."""
    token = pyjwt.encode(
        {
            "uid": "test-user-456",
            "email": "user2@example.com",
            "role": "user",
            "permissions": {},
        },
        "test-jwt-secret-for-testing",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}
