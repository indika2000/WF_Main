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
    # user_permissions: unique on user_id
    await db.user_permissions.create_index("user_id", unique=True)
    await db.user_permissions.create_index("role")
    await db.user_permissions.create_index("is_premium")

    # subscriptions: unique on user_id, sparse unique on stripe_subscription_id
    await db.subscriptions.create_index("user_id", unique=True)
    await db.subscriptions.create_index(
        "stripe_subscription_id", unique=True, sparse=True
    )
    await db.subscriptions.create_index("status")
    await db.subscriptions.create_index("tier")

    # feature_usage: compound unique on (user_id, feature)
    await db.feature_usage.create_index(
        [("user_id", 1), ("feature", 1)], unique=True
    )
    await db.feature_usage.create_index("period_end")
