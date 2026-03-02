import redis.asyncio as aioredis
from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings


# ── MongoDB ──────────────────────────────────────────────────────────────────


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
    # commerce_profiles
    await db.commerce_profiles.create_index("user_id", unique=True)
    await db.commerce_profiles.create_index(
        "stripe_customer_id", unique=True, sparse=True
    )

    # orders
    await db.orders.create_index("order_id", unique=True)
    await db.orders.create_index("user_id")
    await db.orders.create_index([("created_at", -1)])
    await db.orders.create_index("status")

    # subscription_records
    await db.subscription_records.create_index("user_id", unique=True)
    await db.subscription_records.create_index(
        "stripe_subscription_id", unique=True
    )
    await db.subscription_records.create_index("status")


# ── Redis ────────────────────────────────────────────────────────────────────


async def connect_redis() -> aioredis.Redis:
    """Create an async Redis connection."""
    return aioredis.from_url(settings.redis_url, decode_responses=True)


async def close_redis(r: aioredis.Redis) -> None:
    """Close the Redis connection."""
    await r.aclose()


async def get_redis(request: Request) -> aioredis.Redis:
    """FastAPI dependency that returns the Redis instance from app state."""
    return request.app.state.redis
