from pydantic_settings import BaseSettings


class BaseServiceConfig(BaseSettings):
    """Base configuration shared by all Python services."""

    service_name: str = "unknown"
    mongodb_uri: str = "mongodb://mongodb:27017/wildernessfriends"
    redis_url: str = "redis://redis:6379"
    internal_api_key: str = "change-me"
    jwt_secret: str = "change-me"
    debug: bool = False

    model_config = {"env_file": ".env", "extra": "allow"}
