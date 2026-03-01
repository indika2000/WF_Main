"""Integration tests for user image listing routes."""

import pytest

from tests.conftest import create_test_image


@pytest.mark.asyncio
class TestUserImageRoutes:
    async def _upload_image(self, test_client, headers, category="general"):
        image_data = create_test_image()
        response = await test_client.post(
            "/images/upload",
            files={"file": ("test.png", image_data, "image/png")},
            data={"category": category},
            headers=headers,
        )
        return response.json()["data"]["id"]

    async def test_list_user_images(self, test_client, auth_headers):
        await self._upload_image(test_client, auth_headers)
        await self._upload_image(test_client, auth_headers)

        response = await test_client.get(
            "/images/user/test-user-123",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)
        assert len(data["data"]) >= 2

    async def test_list_user_images_wrong_user(self, test_client, auth_headers):
        response = await test_client.get(
            "/images/user/other-user",
            headers=auth_headers,
        )
        assert response.status_code == 403

    async def test_list_user_images_by_category(self, test_client, auth_headers):
        await self._upload_image(test_client, auth_headers, category="profile")
        await self._upload_image(test_client, auth_headers, category="general")

        response = await test_client.get(
            "/images/user/test-user-123/profile",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert all(img["category"] == "profile" for img in data)

    async def test_list_with_pagination(self, test_client, auth_headers):
        for _ in range(3):
            await self._upload_image(test_client, auth_headers)

        response = await test_client.get(
            "/images/user/test-user-123?page=1&limit=2",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert len(response.json()["data"]) <= 2

    async def test_service_can_list_any_user(self, test_client, api_key_headers):
        """Service-to-service calls should bypass user check."""
        response = await test_client.get(
            "/images/user/any-user",
            headers=api_key_headers,
        )
        assert response.status_code == 200
