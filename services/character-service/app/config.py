from shared.python.config import BaseServiceConfig


class CharacterConfig(BaseServiceConfig):
    """Configuration for the Character Service."""

    service_name: str = "character"
    port: int = 5002
    mongodb_db: str = "wildernessfriends"

    # Generation config file path
    generation_config_path: str = "/app/config/generation_v1.yml"

    # Inter-service URLs
    permissions_service_url: str = "http://permissions:5003"
    llm_service_url: str = "http://llm-service:5000"
    image_service_url: str = "http://image-service:5001"


settings = CharacterConfig()
