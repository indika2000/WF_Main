import os

# Set test environment variables before importing the app
os.environ["MONGODB_URI"] = "mongodb://localhost:27017/test_db"
os.environ["INTERNAL_API_KEY"] = "test-api-key"
os.environ["JWT_SECRET"] = "test-jwt-secret-for-testing"
os.environ["SERVICE_NAME"] = "permissions-test"

import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
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
