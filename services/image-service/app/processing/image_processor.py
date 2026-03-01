import io
import logging

from PIL import Image

from app.config import settings
from app.models.images import PROCESSING_PRESETS

logger = logging.getLogger("image")


def get_image_dimensions(data: bytes) -> tuple[int, int]:
    """Get width and height from image bytes."""
    img = Image.open(io.BytesIO(data))
    return img.size


def validate_image_file(data: bytes, content_type: str) -> bool:
    """Validate that the file is a genuine image.

    Uses Pillow to verify the image can be opened and decoded.
    """
    if content_type not in settings.allowed_types_list:
        return False

    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        return True
    except Exception:
        return False


def process_image(
    data: bytes,
    preset_name: str = "general",
    output_format: str = "WEBP",
) -> dict[str, dict]:
    """Generate image variants (thumb, medium, large) from original image data.

    Returns a dict mapping variant name to {data: bytes, width: int, height: int}.
    """
    preset = PROCESSING_PRESETS.get(preset_name, PROCESSING_PRESETS["general"])
    variants = {}

    original = Image.open(io.BytesIO(data))
    # Convert to RGB if necessary (e.g., RGBA PNGs, palette images)
    if original.mode not in ("RGB", "RGBA"):
        original = original.convert("RGB")

    for variant_name, (target_w, target_h) in preset.items():
        # Skip if original is smaller than target
        if original.width <= target_w and original.height <= target_h:
            resized = original.copy()
        else:
            resized = original.copy()
            resized.thumbnail((target_w, target_h), Image.LANCZOS)

        buf = io.BytesIO()
        save_kwargs = {}
        if output_format.upper() == "WEBP":
            save_kwargs["quality"] = settings.image_webp_quality
        elif output_format.upper() == "JPEG":
            save_kwargs["quality"] = settings.image_jpeg_quality
            # JPEG doesn't support alpha
            if resized.mode == "RGBA":
                resized = resized.convert("RGB")

        resized.save(buf, format=output_format, **save_kwargs)
        buf.seek(0)

        variants[variant_name] = {
            "data": buf.read(),
            "width": resized.width,
            "height": resized.height,
        }

    return variants
