"""Integration tests for generation routes."""

import pytest


@pytest.mark.asyncio
class TestTextGeneration:
    async def test_generate_text(self, test_client, api_key_headers):
        response = await test_client.post(
            "/generate/text",
            json={"prompt": "Say hello"},
            headers=api_key_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["content"] == "Mock response"
        assert data["data"]["provider"] == "mock-text"

    async def test_generate_text_with_config(self, test_client, api_key_headers):
        response = await test_client.post(
            "/generate/text",
            json={
                "prompt": "Hello",
                "config": {"max_tokens": 100, "temperature": 0.5},
            },
            headers=api_key_headers,
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    async def test_generate_text_unauthorized(self, test_client):
        response = await test_client.post(
            "/generate/text",
            json={"prompt": "Hello"},
        )
        assert response.status_code == 401

    async def test_generate_text_with_auth(self, test_client, auth_headers):
        response = await test_client.post(
            "/generate/text",
            json={"prompt": "Hello"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    async def test_stream_text(self, test_client, api_key_headers):
        response = await test_client.post(
            "/generate/text/stream",
            json={"prompt": "Hello"},
            headers=api_key_headers,
        )
        assert response.status_code == 200
        # SSE response type
        assert "text/event-stream" in response.headers.get("content-type", "")


@pytest.mark.asyncio
class TestImageGeneration:
    async def test_generate_image(self, test_client, api_key_headers):
        response = await test_client.post(
            "/generate/image",
            json={"prompt": "A beautiful sunset"},
            headers=api_key_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["images"]) == 1
        assert data["data"]["provider"] == "mock-image"

    async def test_generate_image_with_config(self, test_client, api_key_headers):
        response = await test_client.post(
            "/generate/image",
            json={
                "prompt": "A cat",
                "config": {"size": "512x512", "quality": "hd"},
            },
            headers=api_key_headers,
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    async def test_generate_image_unauthorized(self, test_client):
        response = await test_client.post(
            "/generate/image",
            json={"prompt": "A cat"},
        )
        assert response.status_code == 401
