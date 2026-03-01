"""Integration tests for chat routes."""

import pytest


@pytest.mark.asyncio
class TestChatRoutes:
    async def test_send_message(self, test_client, auth_headers):
        response = await test_client.post(
            "/chat",
            json={"message": "Hello!"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["content"] == "Mock response"
        assert data["data"]["conversation_id"] is not None

    async def test_send_message_creates_conversation(self, test_client, auth_headers):
        response = await test_client.post(
            "/chat",
            json={"message": "Start a chat"},
            headers=auth_headers,
        )
        conv_id = response.json()["data"]["conversation_id"]

        # Continue the conversation
        response2 = await test_client.post(
            "/chat",
            json={"message": "Follow up", "conversation_id": conv_id},
            headers=auth_headers,
        )
        assert response2.status_code == 200
        assert response2.json()["data"]["conversation_id"] == conv_id

    async def test_send_message_unauthorized(self, test_client):
        response = await test_client.post(
            "/chat",
            json={"message": "Hello"},
        )
        assert response.status_code == 401

    async def test_stream_message(self, test_client, auth_headers):
        response = await test_client.post(
            "/chat/stream",
            json={"message": "Hello!"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")


@pytest.mark.asyncio
class TestConversationRoutes:
    async def _create_conversation(self, test_client, auth_headers):
        """Helper to create a conversation and return the conv_id."""
        response = await test_client.post(
            "/chat",
            json={"message": "Test message"},
            headers=auth_headers,
        )
        return response.json()["data"]["conversation_id"]

    async def test_list_conversations(self, test_client, auth_headers):
        # Create a conversation first
        await self._create_conversation(test_client, auth_headers)

        response = await test_client.get(
            "/chat/conversations/test-user-123",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)

    async def test_list_conversations_wrong_user(self, test_client, auth_headers):
        response = await test_client.get(
            "/chat/conversations/other-user",
            headers=auth_headers,
        )
        assert response.status_code == 403

    async def test_get_conversation(self, test_client, auth_headers):
        conv_id = await self._create_conversation(test_client, auth_headers)

        response = await test_client.get(
            f"/chat/conversations/detail/{conv_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["id"] == conv_id
        assert len(data["data"]["messages"]) == 2  # user + assistant

    async def test_get_conversation_not_found(self, test_client, auth_headers):
        response = await test_client.get(
            "/chat/conversations/detail/nonexistent-id",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_delete_conversation(self, test_client, auth_headers):
        conv_id = await self._create_conversation(test_client, auth_headers)

        response = await test_client.delete(
            f"/chat/conversations/detail/{conv_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify it's gone
        response2 = await test_client.get(
            f"/chat/conversations/detail/{conv_id}",
            headers=auth_headers,
        )
        assert response2.status_code == 404

    async def test_update_conversation(self, test_client, auth_headers):
        conv_id = await self._create_conversation(test_client, auth_headers)

        response = await test_client.patch(
            f"/chat/conversations/detail/{conv_id}",
            json={"title": "Updated Title"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["data"]["title"] == "Updated Title"

    async def test_api_key_access(self, test_client, api_key_headers):
        """Service-to-service calls should work for chat."""
        response = await test_client.post(
            "/chat",
            json={"message": "Service call"},
            headers=api_key_headers,
        )
        assert response.status_code == 200
