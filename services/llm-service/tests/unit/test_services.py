"""Unit tests for service layer."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from mongomock_motor import AsyncMongoMockClient

from app.services import generation_service, chat_service


class MockTextProvider:
    name = "mock"
    model = "mock-v1"

    async def generate(self, messages, max_tokens=4096, temperature=0.7):
        return {
            "content": "Generated response",
            "tokens_used": 50,
            "finish_reason": "stop",
        }

    async def stream(self, messages, max_tokens=4096, temperature=0.7):
        for chunk in ["Hello", " ", "world"]:
            yield chunk


class FailingProvider:
    name = "failing"
    model = "fail-v1"

    async def generate(self, messages, **kwargs):
        raise Exception("Provider failed")

    async def stream(self, messages, **kwargs):
        raise Exception("Provider failed")
        yield  # Make it an async generator


@pytest.mark.asyncio
class TestGenerationService:
    @patch("app.services.generation_service.provider_factory")
    async def test_generate_text(self, mock_factory):
        mock_factory.get_text_provider.return_value = MockTextProvider()

        result = await generation_service.generate_text("Hello")
        assert result["content"] == "Generated response"
        assert result["provider"] == "mock"
        assert result["tokens_used"] == 50

    @patch("app.services.generation_service.provider_factory")
    async def test_generate_text_no_provider(self, mock_factory):
        mock_factory.get_text_provider.return_value = None

        with pytest.raises(ValueError, match="No text provider"):
            await generation_service.generate_text("Hello")

    @patch("app.services.generation_service.provider_factory")
    async def test_generate_text_with_fallback(self, mock_factory):
        mock_factory.get_text_provider.return_value = FailingProvider()
        mock_factory.get_fallback_text_provider.return_value = MockTextProvider()

        result = await generation_service.generate_text("Hello")
        assert result["content"] == "Generated response"
        assert result["provider"] == "mock"

    @patch("app.services.generation_service.provider_factory")
    async def test_generate_text_with_system_prompt(self, mock_factory):
        provider = MockTextProvider()
        provider.generate = AsyncMock(return_value={
            "content": "System response",
            "tokens_used": 30,
            "finish_reason": "stop",
        })
        mock_factory.get_text_provider.return_value = provider

        await generation_service.generate_text(
            "Hello",
            config={"system_prompt": "You are helpful"},
        )
        call_args = provider.generate.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages") or call_args[0][0]
        assert messages[0]["role"] == "system"

    @patch("app.services.generation_service.provider_factory")
    async def test_generate_image(self, mock_factory):
        mock_img = MagicMock()
        mock_img.name = "mock-img"
        mock_img.model = "mock-img-v1"
        mock_img.generate = AsyncMock(return_value=[
            {"data": "base64data", "format": "png", "size": "1024x1024"}
        ])
        mock_factory.get_image_provider.return_value = mock_img

        result = await generation_service.generate_image("A cat")
        assert len(result["images"]) == 1
        assert result["provider"] == "mock-img"


@pytest.mark.asyncio
class TestChatService:
    async def _get_db(self):
        client = AsyncMongoMockClient()
        return client["test_chat_db"]

    @patch("app.services.chat_service.provider_factory")
    async def test_send_message_new_conversation(self, mock_factory):
        mock_factory.get_text_provider.return_value = MockTextProvider()
        db = await self._get_db()

        result = await chat_service.send_message(
            message="Hello",
            user_id="user-1",
            db=db,
        )

        assert result["content"] == "Generated response"
        assert result["conversation_id"] is not None
        assert result["provider"] == "mock"

        # Verify conversation was saved
        conv = await db.conversations.find_one({"_id": result["conversation_id"]})
        assert conv is not None
        assert len(conv["messages"]) == 2  # user + assistant

    @patch("app.services.chat_service.provider_factory")
    async def test_send_message_existing_conversation(self, mock_factory):
        mock_factory.get_text_provider.return_value = MockTextProvider()
        db = await self._get_db()

        # Create first message
        result1 = await chat_service.send_message(
            message="Hello",
            user_id="user-1",
            db=db,
        )
        conv_id = result1["conversation_id"]

        # Send second message
        result2 = await chat_service.send_message(
            message="How are you?",
            user_id="user-1",
            db=db,
            conversation_id=conv_id,
        )

        assert result2["conversation_id"] == conv_id

        # Verify messages accumulated
        conv = await db.conversations.find_one({"_id": conv_id})
        assert len(conv["messages"]) == 4  # 2 user + 2 assistant

    @patch("app.services.chat_service.provider_factory")
    async def test_send_message_wrong_user(self, mock_factory):
        mock_factory.get_text_provider.return_value = MockTextProvider()
        db = await self._get_db()

        result = await chat_service.send_message(
            message="Hello",
            user_id="user-1",
            db=db,
        )

        with pytest.raises(ValueError, match="not found"):
            await chat_service.send_message(
                message="Hijack",
                user_id="user-2",
                db=db,
                conversation_id=result["conversation_id"],
            )

    async def test_list_conversations(self):
        db = await self._get_db()

        # Insert some conversations
        for i in range(3):
            await db.conversations.insert_one({
                "_id": f"conv-{i}",
                "user_id": "user-1",
                "title": f"Chat {i}",
                "messages": [{"role": "user", "content": "hi"}],
                "updated_at": f"2026-01-0{i+1}",
            })

        results = await chat_service.list_conversations("user-1", db)
        assert len(results) == 3
        # Messages should not be included in listing
        for r in results:
            assert "messages" not in r

    async def test_get_conversation(self):
        db = await self._get_db()

        await db.conversations.insert_one({
            "_id": "conv-get",
            "user_id": "user-1",
            "title": "Test",
            "messages": [{"role": "user", "content": "hello"}],
        })

        conv = await chat_service.get_conversation("conv-get", "user-1", db)
        assert conv is not None
        assert conv["id"] == "conv-get"
        assert len(conv["messages"]) == 1

    async def test_get_conversation_wrong_user(self):
        db = await self._get_db()

        await db.conversations.insert_one({
            "_id": "conv-private",
            "user_id": "user-1",
            "title": "Private",
            "messages": [],
        })

        conv = await chat_service.get_conversation("conv-private", "user-2", db)
        assert conv is None

    async def test_delete_conversation(self):
        db = await self._get_db()

        await db.conversations.insert_one({
            "_id": "conv-del",
            "user_id": "user-1",
            "title": "To Delete",
            "messages": [],
        })

        deleted = await chat_service.delete_conversation("conv-del", "user-1", db)
        assert deleted is True

        # Verify gone
        doc = await db.conversations.find_one({"_id": "conv-del"})
        assert doc is None

    async def test_delete_conversation_not_found(self):
        db = await self._get_db()
        deleted = await chat_service.delete_conversation("nonexistent", "user-1", db)
        assert deleted is False

    async def test_update_conversation(self):
        db = await self._get_db()

        await db.conversations.insert_one({
            "_id": "conv-upd",
            "user_id": "user-1",
            "title": "Old Title",
            "messages": [],
        })

        conv = await chat_service.update_conversation(
            "conv-upd", "user-1", {"title": "New Title"}, db
        )
        assert conv["title"] == "New Title"
