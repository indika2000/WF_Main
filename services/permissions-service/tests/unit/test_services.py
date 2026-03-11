import pytest
from mongomock_motor import AsyncMongoMockClient

from app.services.permissions_service import (
    check_permission,
    create_default_permissions,
    get_permissions,
    sync_permissions_to_tier,
    update_permissions,
)
from app.services.usage_service import check_usage, record_usage, add_bonus


@pytest.fixture
async def db():
    client = AsyncMongoMockClient()
    db = client["test_db"]
    yield db
    client.close()


class TestPermissionsService:
    @pytest.mark.asyncio
    async def test_create_default_permissions(self, db):
        result = await create_default_permissions("user123", db, "test@example.com")
        assert result is not None
        assert result["user_id"] == "user123"
        assert result["role"] == "user"
        assert result["is_premium"] is False
        # Free tier gives ai_text_generation
        assert result["permissions"]["ai_text_generation"] is True
        assert result["permissions"]["ai_image_generation"] is False

    @pytest.mark.asyncio
    async def test_duplicate_user_returns_none(self, db):
        await create_default_permissions("user123", db)
        result = await create_default_permissions("user123", db)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_permissions(self, db):
        await create_default_permissions("user123", db)
        result = await get_permissions("user123", db)
        assert result is not None
        assert result["user_id"] == "user123"

    @pytest.mark.asyncio
    async def test_get_nonexistent_user(self, db):
        result = await get_permissions("nonexistent", db)
        assert result is None

    @pytest.mark.asyncio
    async def test_update_permissions(self, db):
        await create_default_permissions("user123", db)
        result = await update_permissions(
            "user123",
            {"permissions": {"ad_free": True}},
            db,
        )
        assert result is not None
        assert result["permissions"]["ad_free"] is True

    @pytest.mark.asyncio
    async def test_check_permission_true(self, db):
        await create_default_permissions("user123", db)
        result = await check_permission("user123", "ai_text_generation", db)
        assert result["allowed"] is True

    @pytest.mark.asyncio
    async def test_check_permission_false(self, db):
        await create_default_permissions("user123", db)
        result = await check_permission("user123", "ai_image_generation", db)
        assert result["allowed"] is False

    @pytest.mark.asyncio
    async def test_sync_to_premium_tier(self, db):
        await create_default_permissions("user123", db)
        result = await sync_permissions_to_tier("user123", "premium", db)
        assert result["is_premium"] is True
        assert result["permissions"]["ad_free"] is True
        assert result["permissions"]["ai_image_generation"] is True
        assert result["permissions"]["advanced_search"] is True

    @pytest.mark.asyncio
    async def test_sync_to_ultra_tier(self, db):
        await create_default_permissions("user123", db)
        result = await sync_permissions_to_tier("user123", "ultra", db)
        assert result["is_premium"] is True
        assert result["permissions"]["unlimited_storage"] is True
        assert result["permissions"]["priority_support"] is True


class TestUsageService:
    @pytest.mark.asyncio
    async def test_check_usage_within_limit(self, db):
        # Create user (initializes usage records)
        await create_default_permissions("user123", db)
        # Record some usage
        await record_usage("user123", "ai_text_generation", db)
        result = await check_usage("user123", "ai_text_generation", db)
        assert result["allowed"] is True
        assert result["used"] == 1
        assert result["limit"] == 10  # Free tier limit
        assert result["remaining"] == 9

    @pytest.mark.asyncio
    async def test_check_usage_at_limit(self, db):
        await create_default_permissions("user123", db)
        # Use all 10 free tier uses
        for _ in range(10):
            await record_usage("user123", "ai_text_generation", db)
        result = await check_usage("user123", "ai_text_generation", db)
        assert result["allowed"] is False
        assert result["remaining"] == 0
        assert result["reason"] == "limit_reached"

    @pytest.mark.asyncio
    async def test_check_usage_not_found(self, db):
        result = await check_usage("user123", "nonexistent_feature", db)
        assert result["allowed"] is False
        assert result["reason"] == "feature_not_found"

    @pytest.mark.asyncio
    async def test_bonus_adds_to_limit(self, db):
        await create_default_permissions("user123", db)
        # Use all 10 free tier uses
        for _ in range(10):
            await record_usage("user123", "ai_text_generation", db)
        # Add 5 bonus uses
        await add_bonus("user123", "ai_text_generation", 5, db)
        result = await check_usage("user123", "ai_text_generation", db)
        assert result["allowed"] is True
        assert result["bonus"] == 5
        assert result["remaining"] == 5

    @pytest.mark.asyncio
    async def test_unlimited_usage(self, db):
        await create_default_permissions("user123", db)
        # Upgrade to ultra (unlimited)
        await sync_permissions_to_tier("user123", "ultra", db)
        # Record many uses
        for _ in range(100):
            await record_usage("user123", "ai_text_generation", db)
        result = await check_usage("user123", "ai_text_generation", db)
        assert result["allowed"] is True
        assert result["remaining"] == -1

    @pytest.mark.asyncio
    async def test_character_creation_free_tier(self, db):
        await create_default_permissions("user123", db)
        result = await check_usage("user123", "character_creation", db)
        assert result["allowed"] is True
        assert result["limit"] == 5
        assert result["remaining"] == 5

    @pytest.mark.asyncio
    async def test_character_creation_free_limit(self, db):
        await create_default_permissions("user123", db)
        for _ in range(5):
            await record_usage("user123", "character_creation", db)
        result = await check_usage("user123", "character_creation", db)
        assert result["allowed"] is False
        assert result["remaining"] == 0

    @pytest.mark.asyncio
    async def test_character_creation_premium_tier(self, db):
        await create_default_permissions("user123", db)
        await sync_permissions_to_tier("user123", "premium", db)
        result = await check_usage("user123", "character_creation", db)
        assert result["allowed"] is True
        assert result["limit"] == 25

    @pytest.mark.asyncio
    async def test_character_creation_ultra_tier(self, db):
        await create_default_permissions("user123", db)
        await sync_permissions_to_tier("user123", "ultra", db)
        result = await check_usage("user123", "character_creation", db)
        assert result["allowed"] is True
        assert result["limit"] == 50
