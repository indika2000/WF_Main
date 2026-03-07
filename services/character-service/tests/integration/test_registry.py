"""Integration tests for the registry service — supply caps, collisions."""

import pytest

from app.models.creature import CreatureCard
from app.services.config_loader import get_config
from app.services.generator import generate_creature
from app.services.registry import (
    add_to_collection,
    check_collision,
    check_supply_cap,
    get_supply_status,
    get_user_collection,
    increment_supply_counter,
    register_creature,
)


class TestSupplyCounters:
    """Test supply cap enforcement with atomic counters."""

    async def test_increment_counter_success(self, test_db):
        result = await increment_supply_counter(test_db, "LEGENDARY", "v1")
        assert result is True

    async def test_counter_tracks_count(self, test_db):
        for _ in range(5):
            await increment_supply_counter(test_db, "LEGENDARY", "v1")

        counter = await test_db.supply_counters.find_one(
            {"counter_key": "rarity:LEGENDARY", "season": "v1"}
        )
        assert counter["current_count"] == 5

    async def test_counter_respects_cap(self, test_db):
        config = get_config()
        cap = config.supply_caps["LEGENDARY"]

        # Fill up to cap
        for _ in range(cap):
            result = await increment_supply_counter(test_db, "LEGENDARY", "v1")
            assert result is True

        # Next one should fail
        result = await increment_supply_counter(test_db, "LEGENDARY", "v1")
        assert result is False

    async def test_unlimited_cap(self, test_db):
        # COMMON has null cap (unlimited)
        for _ in range(100):
            result = await increment_supply_counter(test_db, "COMMON", "v1")
            assert result is True

    async def test_supply_status(self, test_db):
        await increment_supply_counter(test_db, "RARE", "v1")
        await increment_supply_counter(test_db, "RARE", "v1")

        status = await get_supply_status(test_db, "v1")
        rare_status = next(s for s in status if s["rarity"] == "RARE")
        assert rare_status["current_count"] == 2
        assert rare_status["max_count"] == 25000


class TestCollisionDetection:
    """Test collision policies per rarity tier."""

    async def test_common_no_collision(self, test_db):
        config = get_config()
        creature = generate_creature(
            "EAN_13", "5012345678900", "5012345678900",
            "EAN_13|5012345678900|WILDERNESS_FRIENDS|v1", config
        )
        creature.classification.rarity = "COMMON"
        assert await check_collision(test_db, creature) is False

    async def test_uncommon_no_collision(self, test_db):
        config = get_config()
        creature = generate_creature(
            "EAN_13", "5012345678900", "5012345678900",
            "EAN_13|5012345678900|WILDERNESS_FRIENDS|v1", config
        )
        creature.classification.rarity = "UNCOMMON"
        assert await check_collision(test_db, creature) is False

    async def test_epic_collision_with_same_signature(self, test_db):
        config = get_config()
        # Create a creature and persist it
        c1 = generate_creature(
            "EAN_13", "5012345678900", "5012345678900",
            "EAN_13|5012345678900|WILDERNESS_FRIENDS|v1", config
        )
        c1.classification.rarity = "EPIC"
        await test_db.creatures.insert_one(c1.to_db_dict())

        # Create another creature with the same signature but different source
        c2 = generate_creature(
            "EAN_13", "4006381333931", "4006381333931",
            "EAN_13|4006381333931|WILDERNESS_FRIENDS|v1", config
        )
        c2.classification.rarity = "EPIC"
        # Force same signature for testing
        c2.identity.creature_signature = c1.identity.creature_signature

        assert await check_collision(test_db, c2) is True


class TestCreatureRegistration:
    """Test the full registration flow."""

    async def test_register_new_creature(self, test_db):
        config = get_config()
        creature = generate_creature(
            "EAN_13", "5012345678900", "5012345678900",
            "EAN_13|5012345678900|WILDERNESS_FRIENDS|v1", config
        )
        result = await register_creature(test_db, creature, "user-123")
        assert result.identity.creature_id == creature.identity.creature_id
        assert result.claimed_by == "user-123"
        assert result.status == "claimed"

    async def test_register_idempotent(self, test_db):
        config = get_config()
        creature = generate_creature(
            "EAN_13", "5012345678900", "5012345678900",
            "EAN_13|5012345678900|WILDERNESS_FRIENDS|v1", config
        )
        r1 = await register_creature(test_db, creature, "user-123")
        r2 = await register_creature(test_db, creature, "user-123")
        assert r1.identity.creature_id == r2.identity.creature_id


class TestUserCollection:
    """Test user collection management."""

    async def test_add_to_collection(self, test_db):
        added = await add_to_collection(
            test_db, "user-123", "creature-abc", "EAN_13|123|WF|v1"
        )
        assert added is True

    async def test_add_duplicate_rejected(self, test_db):
        await add_to_collection(
            test_db, "user-123", "creature-abc", "EAN_13|123|WF|v1"
        )
        added = await add_to_collection(
            test_db, "user-123", "creature-abc", "EAN_13|123|WF|v1"
        )
        assert added is False

    async def test_different_users_can_own_same_creature(self, test_db):
        a1 = await add_to_collection(
            test_db, "user-123", "creature-abc", "EAN_13|123|WF|v1"
        )
        a2 = await add_to_collection(
            test_db, "user-456", "creature-abc", "EAN_13|123|WF|v1"
        )
        assert a1 is True
        assert a2 is True

    async def test_get_user_collection(self, test_db):
        await add_to_collection(
            test_db, "user-123", "creature-abc", "EAN_13|123|WF|v1"
        )
        await add_to_collection(
            test_db, "user-123", "creature-def", "EAN_13|456|WF|v1"
        )
        items = await get_user_collection(test_db, "user-123")
        assert len(items) == 2
