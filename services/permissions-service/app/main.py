import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import close_db, connect_db, init_indexes
from app.routes import admin, health, permissions, subscriptions, usage
from shared.python.middleware import RequestLoggingMiddleware, global_exception_handler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(settings.service_name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle — connect/disconnect MongoDB."""
    logger.info("Starting %s service...", settings.service_name)
    client, db = await connect_db()
    app.state.db = db
    app.state.mongo_client = client
    await init_indexes(db)
    logger.info("Connected to MongoDB, indexes created")
    yield
    await close_db(client)
    logger.info("Disconnected from MongoDB")


app = FastAPI(
    title="Permissions Service",
    description="User permissions, subscriptions, and feature usage metering",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware, service_name="PERMISSIONS")

# Exception handler
app.add_exception_handler(Exception, global_exception_handler)

# Routes
app.include_router(health.router, tags=["Health"])
app.include_router(permissions.router, tags=["Permissions"])
app.include_router(subscriptions.router, tags=["Subscriptions"])
app.include_router(usage.router, tags=["Usage"])
app.include_router(admin.router, tags=["Admin"])
