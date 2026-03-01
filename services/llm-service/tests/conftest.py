import os

# Set test environment variables before importing the app
os.environ["MONGODB_URI"] = "mongodb://localhost:27017/test_db"
os.environ["INTERNAL_API_KEY"] = "test-api-key"
os.environ["JWT_SECRET"] = "test-jwt-secret-for-testing"
os.environ["SERVICE_NAME"] = "llm-test"
os.environ["LLM_CONFIG_PATH"] = "/nonexistent/providers.yml"

import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.providers.factory import provider_factory


class MockTextProvider:
    """Mock text provider for testing."""

    name = "mock-text"
    model = "mock-model-v1"

    async def generate(self, messages, max_tokens=4096, temperature=0.7):
        return {
            "content": "Mock response",
            "tokens_used": 42,
            "finish_reason": "stop",
        }

    async def stream(self, messages, max_tokens=4096, temperature=0.7):
        for chunk in ["Mock ", "stream ", "response"]:
            yield chunk


class MockImageProvider:
    """Mock image provider for testing."""

    name = "mock-image"
    model = "mock-image-v1"

    async def generate(self, prompt, size="1024x1024", quality="standard", n=1):
        return [
            {
                "data": "bW9jayBpbWFnZSBkYXRh",  # base64 "mock image data"
                "format": "png",
                "size": size,
            }
        ]


@pytest.fixture
async def test_db():
    """Provide a clean test MongoDB for each test."""
    client = AsyncMongoMockClient()
    db = client["test_db"]
    yield db
    client.close()


@pytest.fixture
async def test_client(test_db):
    """Provide an async HTTP test client with injected test DB and mock providers."""
    app.state.db = test_db

    # Inject mock providers
    provider_factory._text_providers = {"mock-text": MockTextProvider()}
    provider_factory._image_providers = {"mock-image": MockImageProvider()}
    provider_factory._text_config = {"primary": "mock-text"}
    provider_factory._image_config = {"primary": "mock-image"}

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
