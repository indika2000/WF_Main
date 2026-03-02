from shared.python.config import BaseServiceConfig


class CommerceConfig(BaseServiceConfig):
    """Configuration for the Commerce Service."""

    service_name: str = "commerce"
    port: int = 3004
    mongodb_db: str = "wildernessfriends"

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_premium: str = ""
    stripe_price_ultra: str = ""

    # Service URLs
    permissions_service_url: str = "http://permissions:5003"

    # Cart
    cart_ttl_seconds: int = 604800  # 7 days


settings = CommerceConfig()
