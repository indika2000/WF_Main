"""Integration tests for provider routes."""

import pytest


@pytest.mark.asyncio
class TestProviderRoutes:
    async def test_list_providers(self, test_client, api_key_headers):
        response = await test_client.get(
            "/providers",
            headers=api_key_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)
        # Should include our mock providers at minimum
        names = [p["name"] for p in data["data"]]
        assert "mock-text" in names or "mock-image" in names

    async def test_list_providers_unauthorized(self, test_client):
        response = await test_client.get("/providers")
        assert response.status_code == 401

    async def test_list_providers_with_auth(self, test_client, auth_headers):
        response = await test_client.get(
            "/providers",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    async def test_check_provider_status(self, test_client, api_key_headers):
        response = await test_client.get(
            "/providers/mock-text/status",
            headers=api_key_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "mock-text"

    async def test_check_unavailable_provider(self, test_client, api_key_headers):
        response = await test_client.get(
            "/providers/nonexistent/status",
            headers=api_key_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "unavailable"
