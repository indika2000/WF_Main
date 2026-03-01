import logging
from pathlib import Path
from typing import Any

import yaml

from app.config import settings

logger = logging.getLogger("llm")


class ProviderFactory:
    """Factory for creating and managing AI provider instances.

    Loads configuration from providers.yml, instantiates only providers
    whose API keys are available, and supports fallback chains.
    """

    def __init__(self):
        self._text_providers: dict[str, Any] = {}
        self._image_providers: dict[str, Any] = {}
        self._config: dict[str, Any] = {}
        self._text_config: dict[str, Any] = {}
        self._image_config: dict[str, Any] = {}

    def initialize(self) -> None:
        """Load config and instantiate available providers."""
        self._load_config()
        self._init_text_providers()
        self._init_image_providers()

        available_text = list(self._text_providers.keys())
        available_image = list(self._image_providers.keys())
        logger.info(
            "Providers initialized — text: %s, image: %s",
            available_text or "none",
            available_image or "none",
        )

    def _load_config(self) -> None:
        config_path = Path(settings.llm_config_path)
        if config_path.exists():
            with open(config_path) as f:
                self._config = yaml.safe_load(f) or {}
        else:
            logger.warning("Provider config not found at %s, using defaults", config_path)
            self._config = {}

        providers = self._config.get("providers", {})
        self._text_config = providers.get("text", {})
        self._image_config = providers.get("image", {})

    def _init_text_providers(self) -> None:
        provider_configs = self._text_config.get("providers", {})

        # Anthropic
        if settings.anthropic_api_key:
            try:
                from app.providers.anthropic_provider import AnthropicTextProvider

                cfg = provider_configs.get("anthropic", {})
                self._text_providers["anthropic"] = AnthropicTextProvider(
                    api_key=settings.anthropic_api_key,
                    model=cfg.get("model", "claude-sonnet-4-20250514"),
                    timeout=cfg.get("timeout", 30),
                )
            except Exception as e:
                logger.warning("Failed to init Anthropic text provider: %s", e)

        # OpenAI
        if settings.openai_api_key:
            try:
                from app.providers.openai_provider import OpenAITextProvider

                cfg = provider_configs.get("openai", {})
                self._text_providers["openai"] = OpenAITextProvider(
                    api_key=settings.openai_api_key,
                    model=cfg.get("model", "gpt-4o"),
                    timeout=cfg.get("timeout", 30),
                )
            except Exception as e:
                logger.warning("Failed to init OpenAI text provider: %s", e)

        # Gemini
        if settings.google_api_key:
            try:
                from app.providers.gemini_provider import GeminiTextProvider

                cfg = provider_configs.get("gemini", {})
                self._text_providers["gemini"] = GeminiTextProvider(
                    api_key=settings.google_api_key,
                    model=cfg.get("model", "gemini-2.5-flash"),
                    timeout=cfg.get("timeout", 30),
                )
            except Exception as e:
                logger.warning("Failed to init Gemini text provider: %s", e)

    def _init_image_providers(self) -> None:
        provider_configs = self._image_config.get("providers", {})

        # OpenAI (DALL-E)
        if settings.openai_api_key:
            try:
                from app.providers.openai_provider import OpenAIImageProvider

                cfg = provider_configs.get("openai", {})
                self._image_providers["openai"] = OpenAIImageProvider(
                    api_key=settings.openai_api_key,
                    model=cfg.get("model", "dall-e-3"),
                    timeout=cfg.get("timeout", 60),
                )
            except Exception as e:
                logger.warning("Failed to init OpenAI image provider: %s", e)

        # Gemini (Imagen)
        if settings.google_api_key:
            try:
                from app.providers.gemini_provider import GeminiImageProvider

                cfg = provider_configs.get("gemini", {})
                self._image_providers["gemini"] = GeminiImageProvider(
                    api_key=settings.google_api_key,
                    model=cfg.get("model", "imagen-3.0-generate-002"),
                    timeout=cfg.get("timeout", 60),
                )
            except Exception as e:
                logger.warning("Failed to init Gemini image provider: %s", e)

    def get_text_provider(self, name: str | None = None) -> Any:
        """Get a text provider by name, or the configured primary/fallback."""
        if name and name in self._text_providers:
            return self._text_providers[name]

        # Try primary
        primary = self._text_config.get("primary", settings.llm_default_text_provider)
        if primary in self._text_providers:
            return self._text_providers[primary]

        # Try fallback
        fallback = self._text_config.get("fallback")
        if fallback and fallback in self._text_providers:
            return self._text_providers[fallback]

        # Return any available
        if self._text_providers:
            return next(iter(self._text_providers.values()))

        return None

    def get_image_provider(self, name: str | None = None) -> Any:
        """Get an image provider by name, or the configured primary/fallback."""
        if name and name in self._image_providers:
            return self._image_providers[name]

        primary = self._image_config.get("primary", settings.llm_default_image_provider)
        if primary in self._image_providers:
            return self._image_providers[primary]

        fallback = self._image_config.get("fallback")
        if fallback and fallback in self._image_providers:
            return self._image_providers[fallback]

        if self._image_providers:
            return next(iter(self._image_providers.values()))

        return None

    def get_fallback_text_provider(self, exclude: str) -> Any:
        """Get a fallback text provider, excluding the specified one."""
        fallback_name = self._text_config.get("fallback")
        if fallback_name and fallback_name != exclude and fallback_name in self._text_providers:
            return self._text_providers[fallback_name]

        # Try any other available provider
        for name, provider in self._text_providers.items():
            if name != exclude:
                return provider
        return None

    def get_fallback_image_provider(self, exclude: str) -> Any:
        """Get a fallback image provider, excluding the specified one."""
        fallback_name = self._image_config.get("fallback")
        if fallback_name and fallback_name != exclude and fallback_name in self._image_providers:
            return self._image_providers[fallback_name]

        for name, provider in self._image_providers.items():
            if name != exclude:
                return provider
        return None

    def list_providers(self) -> list[dict[str, Any]]:
        """List all providers with their capabilities and status."""
        all_names = set(
            list(self._text_providers.keys())
            + list(self._image_providers.keys())
            + ["anthropic", "openai", "gemini"]
        )

        result = []
        for name in sorted(all_names):
            capabilities = []
            models = []

            if name in self._text_providers:
                capabilities.append("text")
                capabilities.append("streaming")
                models.append(self._text_providers[name].model)
            if name in self._image_providers:
                capabilities.append("image")
                models.append(self._image_providers[name].model)

            status = "available" if capabilities else "no_api_key"
            result.append({
                "name": name,
                "capabilities": capabilities,
                "status": status,
                "models": models,
            })

        return result

    def is_provider_available(self, name: str) -> bool:
        return name in self._text_providers or name in self._image_providers


# Module-level singleton — initialized during FastAPI lifespan
provider_factory = ProviderFactory()
