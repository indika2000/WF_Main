"""Integration tests for image routes."""

import io

import pytest
from PIL import Image

from tests.conftest import create_test_image


@pytest.mark.asyncio
class TestImageUpload:
    async def test_upload_image(self, test_client, api_key_headers):
        image_data = create_test_image()
        response = await test_client.post(
            "/images/upload",
            files={"file": ("test.png", image_data, "image/png")},
            data={"category": "general"},
            headers=api_key_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] is not None
        assert data["data"]["source"] == "upload"

    async def test_upload_with_tags(self, test_client, api_key_headers):
        image_data = create_test_image()
        response = await test_client.post(
            "/images/upload",
            files={"file": ("test.png", image_data, "image/png")},
            data={"category": "profile", "tags": "avatar,user"},
            headers=api_key_headers,
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert "avatar" in data["tags"]
        assert "user" in data["tags"]

    async def test_upload_unauthorized(self, test_client):
        image_data = create_test_image()
        response = await test_client.post(
            "/images/upload",
            files={"file": ("test.png", image_data, "image/png")},
        )
        assert response.status_code == 401

    async def test_upload_invalid_type(self, test_client, api_key_headers):
        response = await test_client.post(
            "/images/upload",
            files={"file": ("test.txt", b"not an image", "text/plain")},
            data={"category": "general"},
            headers=api_key_headers,
        )
        assert response.status_code == 400


@pytest.mark.asyncio
class TestImageRetrieval:
    async def _upload_image(self, test_client, headers):
        image_data = create_test_image()
        response = await test_client.post(
            "/images/upload",
            files={"file": ("test.png", image_data, "image/png")},
            data={"category": "general"},
            headers=headers,
        )
        return response.json()["data"]["id"]

    async def test_get_image_metadata(self, test_client, api_key_headers):
        image_id = await self._upload_image(test_client, api_key_headers)
        response = await test_client.get(
            f"/images/{image_id}",
            headers=api_key_headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == image_id
        assert data["content_type"] == "image/png"

    async def test_get_image_not_found(self, test_client, api_key_headers):
        response = await test_client.get(
            "/images/nonexistent",
            headers=api_key_headers,
        )
        assert response.status_code == 404

    async def test_serve_image_file(self, test_client, api_key_headers):
        image_id = await self._upload_image(test_client, api_key_headers)
        response = await test_client.get(
            f"/images/{image_id}/file",
            headers=api_key_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        # Verify it's valid image data
        img = Image.open(io.BytesIO(response.content))
        assert img.size[0] > 0

    async def test_serve_image_variant(self, test_client, api_key_headers):
        image_id = await self._upload_image(test_client, api_key_headers)
        response = await test_client.get(
            f"/images/{image_id}/file/thumb",
            headers=api_key_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/webp"

    async def test_serve_invalid_variant(self, test_client, api_key_headers):
        image_id = await self._upload_image(test_client, api_key_headers)
        response = await test_client.get(
            f"/images/{image_id}/file/nonexistent",
            headers=api_key_headers,
        )
        assert response.status_code == 404


@pytest.mark.asyncio
class TestImageDeletion:
    async def test_delete_image(self, test_client, api_key_headers):
        image_data = create_test_image()
        upload = await test_client.post(
            "/images/upload",
            files={"file": ("test.png", image_data, "image/png")},
            data={"category": "general"},
            headers=api_key_headers,
        )
        image_id = upload.json()["data"]["id"]

        response = await test_client.delete(
            f"/images/{image_id}",
            headers=api_key_headers,
        )
        assert response.status_code == 200

        # Verify gone
        response2 = await test_client.get(
            f"/images/{image_id}",
            headers=api_key_headers,
        )
        assert response2.status_code == 404

    async def test_delete_not_found(self, test_client, api_key_headers):
        response = await test_client.delete(
            "/images/nonexistent",
            headers=api_key_headers,
        )
        assert response.status_code == 404


@pytest.mark.asyncio
class TestImageUpdate:
    async def test_update_image(self, test_client, api_key_headers):
        image_data = create_test_image()
        upload = await test_client.post(
            "/images/upload",
            files={"file": ("test.png", image_data, "image/png")},
            data={"category": "general"},
            headers=api_key_headers,
        )
        image_id = upload.json()["data"]["id"]

        response = await test_client.patch(
            f"/images/{image_id}",
            json={"category": "profile", "tags": ["avatar"]},
            headers=api_key_headers,
        )
        assert response.status_code == 200
        assert response.json()["data"]["category"] == "profile"
