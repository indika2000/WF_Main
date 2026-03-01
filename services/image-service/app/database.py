import logging

from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

logger = logging.getLogger(settings.service_name)


async def connect_db() -> tuple[AsyncIOMotorClient, AsyncIOMotorDatabase]:
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]
    return client, db


async def close_db(client: AsyncIOMotorClient) -> None:
    client.close()


async def get_db(request: Request) -> AsyncIOMotorDatabase:
    """FastAPI dependency — pulls db from app.state set during lifespan."""
    return request.app.state.db


async def init_indexes(db: AsyncIOMotorDatabase) -> None:
    """Create indexes for image service collections."""
    await db.images.create_index("id", unique=True)
    await db.images.create_index("user_id")
    await db.images.create_index([("user_id", 1), ("category", 1)])
    await db.images.create_index("tags")
    await db.images.create_index([("created_at", -1)])

    logger.info("Connected to MongoDB, indexes created")
