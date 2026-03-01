"""Unit tests for Pydantic models."""

import pytest
from app.models.generation import (
    ImageGenConfig,
    ImageGenRequest,
    TextGenConfig,
    TextGenRequest,
)
from app.models.conversations import (
    ChatRequest,
    Conversation,
    ConversationCreate,
    ConversationUpdate,
    Message,
)
from app.models.providers import ProviderInfo, ProviderStatus


class TestTextGenModels:
    def test_text_gen_config_defaults(self):
        config = TextGenConfig()
        assert config.provider is None
        assert config.model is None
        assert config.max_tokens == 4096
        assert config.temperature == 0.7
        assert config.system_prompt is None

    def test_text_gen_request_minimal(self):
        req = TextGenRequest(prompt="Hello")
        assert req.prompt == "Hello"
        assert req.config.max_tokens == 4096

    def test_text_gen_request_with_config(self):
        req = TextGenRequest(
            prompt="Hello",
            config=TextGenConfig(provider="openai", max_tokens=100),
        )
        assert req.config.provider == "openai"
        assert req.config.max_tokens == 100


class TestImageGenModels:
    def test_image_gen_config_defaults(self):
        config = ImageGenConfig()
        assert config.provider is None
        assert config.size == "1024x1024"
        assert config.quality == "standard"
        assert config.n == 1

    def test_image_gen_request(self):
        req = ImageGenRequest(prompt="A cat")
        assert req.prompt == "A cat"
        assert req.config.size == "1024x1024"


class TestConversationModels:
    def test_message_defaults(self):
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.timestamp is not None
        assert msg.provider is None

    def test_conversation_create(self):
        create = ConversationCreate(title="Test Chat")
        assert create.title == "Test Chat"
        assert create.system_prompt is None

    def test_conversation_update_partial(self):
        update = ConversationUpdate(title="New Title")
        assert update.title == "New Title"
        assert update.system_prompt is None
        assert update.metadata is None

    def test_chat_request(self):
        req = ChatRequest(message="Hello")
        assert req.message == "Hello"
        assert req.conversation_id is None
        assert req.config == {}


class TestProviderModels:
    def test_provider_info(self):
        info = ProviderInfo(
            name="openai",
            capabilities=["text", "streaming"],
            status="available",
            models=["gpt-4o"],
        )
        assert info.name == "openai"
        assert "text" in info.capabilities
