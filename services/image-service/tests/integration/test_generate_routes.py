"""Integration tests for AI image generation routes."""

import json

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
class TestGenerateRoutes:
    @patch("app.services.generation_proxy.httpx.AsyncClient")
    async def test_generate_image(self, mock_client_cls, test_client, api_key_headers):
        """Test AI image generation with mocked LLM service response."""
        # Mock the httpx response from LLM service
        import base64

        mock_image_b64 = base64.b64encode(
            # Create a tiny valid PNG (1x1 red pixel)
            _create_minimal_png()
        ).decode("utf-8")

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "images": [
                    {"data": mock_image_b64, "format": "png", "size": "1024x1024"}
                ],
                "provider": "mock-provider",
                "model": "mock-model",
            },
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        response = await test_client.post(
            "/images/generate",
            json={"prompt": "A beautiful sunset over mountains"},
            headers=api_key_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) >= 1
        assert data["data"][0]["source"] == "ai_generated"

    async def test_generate_unauthorized(self, test_client):
        response = await test_client.post(
            "/images/generate",
            json={"prompt": "A cat"},
        )
        assert response.status_code == 401

    async def test_generate_with_options(self, test_client, api_key_headers):
        """Test that generation request accepts optional parameters."""
        # This will fail at the httpx call level, but validates request parsing
        with patch("app.services.generation_proxy.httpx.AsyncClient") as mock_cls:
            mock_resp = AsyncMock()
            mock_resp.status_code = 500
            mock_resp.text = "Service unavailable"

            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            response = await test_client.post(
                "/images/generate",
                json={
                    "prompt": "A cat",
                    "category": "profile",
                    "size": "512x512",
                    "tags": ["test", "ai"],
                },
                headers=api_key_headers,
            )
            # Should fail gracefully (LLM service returns 500)
            assert response.status_code == 400


def _create_minimal_png() -> bytes:
    """Create a minimal valid PNG image for testing."""
    import io
    from PIL import Image

    img = Image.new("RGB", (10, 10), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()
