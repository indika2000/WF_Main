"""Unit tests for provider factory."""

import pytest
from unittest.mock import MagicMock, patch

from app.providers.factory import ProviderFactory


class MockProvider:
    def __init__(self, name, model):
        self.name = name
        self.model = model


class TestProviderFactory:
    def test_get_text_provider_by_name(self):
        factory = ProviderFactory()
        mock = MockProvider("openai", "gpt-4o")
        factory._text_providers = {"openai": mock}
        assert factory.get_text_provider("openai") is mock

    def test_get_text_provider_primary(self):
        factory = ProviderFactory()
        mock = MockProvider("anthropic", "claude")
        factory._text_providers = {"anthropic": mock}
        factory._text_config = {"primary": "anthropic"}
        assert factory.get_text_provider() is mock

    def test_get_text_provider_fallback(self):
        factory = ProviderFactory()
        mock = MockProvider("openai", "gpt-4o")
        factory._text_providers = {"openai": mock}
        factory._text_config = {"primary": "anthropic", "fallback": "openai"}
        # Primary not available, should use fallback
        assert factory.get_text_provider() is mock

    def test_get_text_provider_any_available(self):
        factory = ProviderFactory()
        mock = MockProvider("gemini", "gemini-2.0-flash")
        factory._text_providers = {"gemini": mock}
        factory._text_config = {"primary": "anthropic"}
        # Primary not available, no fallback configured, returns any
        assert factory.get_text_provider() is mock

    def test_get_text_provider_none_available(self):
        factory = ProviderFactory()
        factory._text_config = {}
        assert factory.get_text_provider() is None

    def test_get_image_provider_by_name(self):
        factory = ProviderFactory()
        mock = MockProvider("openai", "dall-e-3")
        factory._image_providers = {"openai": mock}
        assert factory.get_image_provider("openai") is mock

    def test_get_image_provider_none(self):
        factory = ProviderFactory()
        factory._image_config = {}
        assert factory.get_image_provider() is None

    def test_fallback_text_provider(self):
        factory = ProviderFactory()
        primary = MockProvider("anthropic", "claude")
        fallback = MockProvider("openai", "gpt-4o")
        factory._text_providers = {"anthropic": primary, "openai": fallback}
        factory._text_config = {"fallback": "openai"}

        result = factory.get_fallback_text_provider("anthropic")
        assert result is fallback

    def test_fallback_excludes_current(self):
        factory = ProviderFactory()
        only = MockProvider("anthropic", "claude")
        factory._text_providers = {"anthropic": only}
        factory._text_config = {}

        result = factory.get_fallback_text_provider("anthropic")
        assert result is None

    def test_list_providers(self):
        factory = ProviderFactory()
        factory._text_providers = {"openai": MockProvider("openai", "gpt-4o")}
        factory._image_providers = {"openai": MockProvider("openai", "dall-e-3")}

        providers = factory.list_providers()
        openai_entry = next(p for p in providers if p["name"] == "openai")
        assert "text" in openai_entry["capabilities"]
        assert "image" in openai_entry["capabilities"]
        assert openai_entry["status"] == "available"

    def test_is_provider_available(self):
        factory = ProviderFactory()
        factory._text_providers = {"anthropic": MockProvider("anthropic", "claude")}
        factory._image_providers = {}

        assert factory.is_provider_available("anthropic") is True
        assert factory.is_provider_available("openai") is False
