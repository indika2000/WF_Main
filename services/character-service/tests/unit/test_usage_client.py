import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.usage_client import check_character_usage, record_character_usage


class TestCheckCharacterUsage:
    @pytest.mark.asyncio
    async def test_allowed(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "allowed": True,
                "used": 2,
                "limit": 5,
                "remaining": 3,
                "bonus": 0,
            },
        }

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("app.services.usage_client.httpx.AsyncClient", return_value=mock_client):
            result = await check_character_usage("user123")

        assert result["allowed"] is True
        assert result["used"] == 2
        assert result["remaining"] == 3

    @pytest.mark.asyncio
    async def test_limit_reached(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "allowed": False,
                "used": 5,
                "limit": 5,
                "remaining": 0,
                "bonus": 0,
                "reason": "limit_reached",
            },
        }

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("app.services.usage_client.httpx.AsyncClient", return_value=mock_client):
            result = await check_character_usage("user123")

        assert result["allowed"] is False
        assert result["remaining"] == 0

    @pytest.mark.asyncio
    async def test_service_error_returns_not_allowed(self):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("app.services.usage_client.httpx.AsyncClient", return_value=mock_client):
            result = await check_character_usage("user123")

        assert result["allowed"] is False
        assert result["reason"] == "service_error"

    @pytest.mark.asyncio
    async def test_http_error_returns_not_allowed(self):
        import httpx

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with patch("app.services.usage_client.httpx.AsyncClient", return_value=mock_client):
            result = await check_character_usage("user123")

        assert result["allowed"] is False
        assert result["reason"] == "service_unavailable"


class TestRecordCharacterUsage:
    @pytest.mark.asyncio
    async def test_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "used": 3,
                "limit": 5,
                "remaining": 2,
                "bonus": 0,
            },
        }

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("app.services.usage_client.httpx.AsyncClient", return_value=mock_client):
            result = await record_character_usage("user123")

        assert result is not None
        assert result["used"] == 3
        assert result["remaining"] == 2

    @pytest.mark.asyncio
    async def test_failure_returns_none(self):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("app.services.usage_client.httpx.AsyncClient", return_value=mock_client):
            result = await record_character_usage("user123")

        assert result is None
