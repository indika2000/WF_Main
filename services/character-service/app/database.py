from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings


async def connect_db() -> tuple[AsyncIOMotorClient, AsyncIOMotorDatabase]:
    """Create a MongoDB connection and return (client, db)."""
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]
    return client, db


async def close_db(client: AsyncIOMotorClient) -> None:
    """Close the MongoDB connection."""
    client.close()


async def get_db(request: Request) -> AsyncIOMotorDatabase:
    """FastAPI dependency that returns the database instance from app state."""
    return request.app.state.db


async def init_indexes(db: AsyncIOMotorDatabase) -> None:
    """Create required indexes for all collections."""
    # Source registry: one creature per canonical_id
    await db.source_registry.create_index("canonical_id", unique=True)
    await db.source_registry.create_index("creature_id")

    # Creatures: lookup by creature_id, filter by rarity/season
    await db.creatures.create_index("identity.creature_id", unique=True)
    await db.creatures.create_index("classification.rarity")
    await db.creatures.create_index("season")
    await db.creatures.create_index("claimed_by")
    await db.creatures.create_index("identity.creature_signature")

    # Supply counters: lookup by key + season
    await db.supply_counters.create_index(
        [("counter_key", 1), ("season", 1)], unique=True
    )

    # User collections: user's creatures, prevent duplicate ownership
    await db.user_collections.create_index(
        [("user_id", 1), ("creature_id", 1)], unique=True
    )
    await db.user_collections.create_index("user_id")
    await db.user_collections.create_index("creature_id")

    # Image generation jobs: unique job_id, worker claim query, creature lookup
    await db.image_generation_jobs.create_index("job_id", unique=True)
    await db.image_generation_jobs.create_index(
        [("status", 1), ("priority", 1), ("created_at", 1)]
    )
    await db.image_generation_jobs.create_index("creature_id")
