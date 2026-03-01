from shared.python.config import BaseServiceConfig


class LLMConfig(BaseServiceConfig):
    service_name: str = "llm"
    port: int = 5000
    mongodb_db: str = "wildernessfriends"

    # Provider API keys
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""

    # Provider defaults
    llm_default_text_provider: str = "anthropic"
    llm_default_image_provider: str = "gemini"
    llm_config_path: str = "/app/config/providers.yml"

    # Conversation limits
    llm_max_conversation_history: int = 50

    # Service URLs
    permissions_service_url: str = "http://permissions:5003"


settings = LLMConfig()
