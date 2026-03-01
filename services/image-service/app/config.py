from shared.python.config import BaseServiceConfig


class ImageConfig(BaseServiceConfig):
    service_name: str = "image"
    port: int = 5001
    mongodb_db: str = "wildernessfriends"

    # Storage
    image_storage_path: str = "/storage"
    image_max_file_size: int = 10_485_760  # 10 MB

    # Allowed MIME types
    image_allowed_types: str = "image/jpeg,image/png,image/webp,image/gif"

    # Processing quality
    image_jpeg_quality: int = 85
    image_webp_quality: int = 80

    # Service URLs
    llm_service_url: str = "http://llm-service:5000"
    permissions_service_url: str = "http://permissions:5003"

    @property
    def allowed_types_list(self) -> list[str]:
        return [t.strip() for t in self.image_allowed_types.split(",")]


settings = ImageConfig()
