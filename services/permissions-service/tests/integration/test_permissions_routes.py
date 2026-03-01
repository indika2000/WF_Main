import pytest


class TestPermissionsRoutes:
    @pytest.mark.asyncio
    async def test_create_permissions(self, test_client, api_key_headers):
        response = await test_client.post(
            "/permissions/user123",
            headers=api_key_headers,
            json={"email": "test@example.com"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["user_id"] == "user123"
        assert data["data"]["role"] == "user"
        assert data["data"]["permissions"]["ad_free"] is False

    @pytest.mark.asyncio
    async def test_create_duplicate_returns_409(self, test_client, api_key_headers):
        await test_client.post(
            "/permissions/user123",
            headers=api_key_headers,
            json={"email": "test@example.com"},
        )
        response = await test_client.post(
            "/permissions/user123",
            headers=api_key_headers,
            json={"email": "test@example.com"},
        )
        assert response.status_code == 409
        assert response.json()["error_code"] == "USER_EXISTS"

    @pytest.mark.asyncio
    async def test_get_permissions(self, test_client, api_key_headers):
        await test_client.post(
            "/permissions/user123",
            headers=api_key_headers,
            json={},
        )
        response = await test_client.get(
            "/permissions/user123", headers=api_key_headers
        )
        assert response.status_code == 200
        assert response.json()["data"]["user_id"] == "user123"

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_404(self, test_client, api_key_headers):
        response = await test_client.get(
            "/permissions/nonexistent", headers=api_key_headers
        )
        assert response.status_code == 404
        assert response.json()["error_code"] == "USER_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_update_permissions(self, test_client, api_key_headers):
        await test_client.post(
            "/permissions/user123",
            headers=api_key_headers,
            json={},
        )
        response = await test_client.patch(
            "/permissions/user123",
            headers=api_key_headers,
            json={"permissions": {"ad_free": True}},
        )
        assert response.status_code == 200
        assert response.json()["data"]["permissions"]["ad_free"] is True

    @pytest.mark.asyncio
    async def test_check_permission_allowed(self, test_client, api_key_headers):
        await test_client.post(
            "/permissions/user123",
            headers=api_key_headers,
            json={},
        )
        response = await test_client.get(
            "/permissions/user123/check/ai_text_generation",
            headers=api_key_headers,
        )
        assert response.status_code == 200
        assert response.json()["data"]["allowed"] is True

    @pytest.mark.asyncio
    async def test_check_permission_denied(self, test_client, api_key_headers):
        await test_client.post(
            "/permissions/user123",
            headers=api_key_headers,
            json={},
        )
        response = await test_client.get(
            "/permissions/user123/check/ai_image_generation",
            headers=api_key_headers,
        )
        assert response.status_code == 200
        assert response.json()["data"]["allowed"] is False

    @pytest.mark.asyncio
    async def test_unauthorized_request(self, test_client):
        response = await test_client.get("/permissions/user123")
        assert response.status_code == 401
