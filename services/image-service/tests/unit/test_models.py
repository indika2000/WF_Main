"""Unit tests for image models."""

from app.models.images import (
    GenerateRequest,
    ImageRecord,
    ImageUpdate,
    ImageUploadMeta,
    ImageVariant,
    PROCESSING_PRESETS,
)


class TestImageModels:
    def test_image_variant(self):
        v = ImageVariant(width=100, height=100, storage_path="/path/thumb.webp")
        assert v.width == 100
        assert v.file_size == 0

    def test_image_record_defaults(self):
        record = ImageRecord(
            id="test-id",
            user_id="user-1",
            filename="test.png",
            content_type="image/png",
            file_size=1024,
            storage_path="/path/original.png",
        )
        assert record.category == "general"
        assert record.source == "upload"
        assert record.variants == {}
        assert record.tags == []

    def test_image_upload_meta_defaults(self):
        meta = ImageUploadMeta()
        assert meta.category == "general"
        assert meta.tags == []

    def test_image_update_partial(self):
        update = ImageUpdate(category="profile")
        assert update.category == "profile"
        assert update.tags is None

    def test_generate_request(self):
        req = GenerateRequest(prompt="A beautiful sunset")
        assert req.prompt == "A beautiful sunset"
        assert req.category == "ai_generated"
        assert req.size == "1024x1024"
        assert req.n == 1


class TestProcessingPresets:
    def test_general_preset_exists(self):
        assert "general" in PROCESSING_PRESETS
        preset = PROCESSING_PRESETS["general"]
        assert "thumb" in preset
        assert "medium" in preset
        assert "large" in preset

    def test_profile_preset(self):
        preset = PROCESSING_PRESETS["profile"]
        assert preset["thumb"] == (64, 64)

    def test_card_preset(self):
        preset = PROCESSING_PRESETS["card"]
        assert preset["thumb"] == (100, 140)
