import io
import os

# Set test environment variables before importing the app
os.environ["MONGODB_URI"] = "mongodb://localhost:27017/test_db"
os.environ["INTERNAL_API_KEY"] = "test-api-key"
os.environ["JWT_SECRET"] = "test-jwt-secret-for-testing"
os.environ["SERVICE_NAME"] = "image-test"
os.environ["IMAGE_STORAGE_PATH"] = "/tmp/image-test-storage"

import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient
from PIL import Image

from app.main import app


class MockStorage:
    """In-memory storage backend for testing."""

    def __init__(self):
        self._data: dict[str, bytes] = {}

    async def save(self, path: str, data: bytes) -> None:
        self._data[path] = data

    async def load(self, path: str) -> bytes:
        if path not in self._data:
            raise FileNotFoundError(f"Not found: {path}")
        return self._data[path]

    async def delete(self, path: str) -> None:
        self._data.pop(path, None)

    async def exists(self, path: str) -> bool:
        return path in self._data

    def get_url(self, path: str) -> str:
        return path


def create_test_image(width=100, height=100, format="PNG") -> bytes:
    """Create a minimal test image in memory."""
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format=format)
    buf.seek(0)
    return buf.read()


@pytest.fixture
async def test_db():
    """Provide a clean test MongoDB for each test."""
    client = AsyncMongoMockClient()
    db = client["test_db"]
    yield db
    client.close()


@pytest.fixture
async def test_client(test_db):
    """Provide an async HTTP test client with mock storage and test DB."""
    app.state.db = test_db
    app.state.storage = MockStorage()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def api_key_headers():
    return {"X-Api-Key": "test-api-key"}


@pytest.fixture
def auth_headers():
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


@pytest.fixture
def test_image_data():
    """Provide test PNG image bytes."""
    return create_test_image()
