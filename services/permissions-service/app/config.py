from shared.python.config import BaseServiceConfig


class PermissionsConfig(BaseServiceConfig):
    """Configuration for the Permissions Service."""

    service_name: str = "permissions"
    port: int = 5003
    mongodb_db: str = "wildernessfriends"


settings = PermissionsConfig()
