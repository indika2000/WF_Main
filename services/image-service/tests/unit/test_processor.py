"""Unit tests for image processor."""

import io

import pytest
from PIL import Image

from app.processing.image_processor import (
    get_image_dimensions,
    process_image,
    validate_image_file,
)


def _make_image(width=200, height=200, fmt="PNG") -> bytes:
    img = Image.new("RGB", (width, height), color=(0, 128, 255))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    buf.seek(0)
    return buf.read()


class TestGetImageDimensions:
    def test_dimensions(self):
        data = _make_image(300, 400)
        w, h = get_image_dimensions(data)
        assert w == 300
        assert h == 400


class TestValidateImageFile:
    def test_valid_png(self):
        data = _make_image(fmt="PNG")
        assert validate_image_file(data, "image/png") is True

    def test_valid_jpeg(self):
        data = _make_image(fmt="JPEG")
        assert validate_image_file(data, "image/jpeg") is True

    def test_invalid_type(self):
        data = _make_image(fmt="PNG")
        assert validate_image_file(data, "text/plain") is False

    def test_invalid_data(self):
        assert validate_image_file(b"not an image", "image/png") is False


class TestProcessImage:
    def test_general_preset(self):
        data = _make_image(800, 600)
        variants = process_image(data, preset_name="general")
        assert "thumb" in variants
        assert "medium" in variants
        assert "large" in variants

        # Check that variants have correct keys
        for name, v in variants.items():
            assert "data" in v
            assert "width" in v
            assert "height" in v
            assert isinstance(v["data"], bytes)
            assert len(v["data"]) > 0

    def test_variants_are_smaller(self):
        data = _make_image(1600, 1200)
        variants = process_image(data, preset_name="general")

        # Thumb should be smaller than original
        assert variants["thumb"]["width"] <= 150
        assert variants["thumb"]["height"] <= 150

    def test_profile_preset(self):
        data = _make_image(500, 500)
        variants = process_image(data, preset_name="profile")
        assert variants["thumb"]["width"] <= 64
        assert variants["thumb"]["height"] <= 64

    def test_small_image_not_upscaled(self):
        data = _make_image(50, 50)
        variants = process_image(data, preset_name="general")
        # Should not upscale — all variants same as original
        assert variants["thumb"]["width"] == 50
        assert variants["thumb"]["height"] == 50

    def test_output_format_jpeg(self):
        data = _make_image(200, 200)
        variants = process_image(data, preset_name="general", output_format="JPEG")
        # Should produce valid JPEG data
        for v in variants.values():
            img = Image.open(io.BytesIO(v["data"]))
            assert img.format == "JPEG"
