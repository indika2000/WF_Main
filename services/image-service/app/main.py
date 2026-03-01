import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import close_db, connect_db, init_indexes
from app.routes import generate, health, images, user_images
from app.storage.local import LocalStorage
from shared.python.middleware import RequestLoggingMiddleware, global_exception_handler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(settings.service_name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle — connect MongoDB, init storage."""
    logger.info("Starting %s service...", settings.service_name)
    client, db = await connect_db()
    app.state.db = db
    app.state.mongo_client = client
    await init_indexes(db)

    # Initialize storage backend
    app.state.storage = LocalStorage(settings.image_storage_path)
    logger.info("Image service ready (storage: %s)", settings.image_storage_path)

    yield
    await close_db(client)
    logger.info("Disconnected from MongoDB")


app = FastAPI(
    title="Image Service",
    description="Image upload, processing, storage, and AI generation",
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
app.add_middleware(RequestLoggingMiddleware, service_name="IMAGE")

# Exception handler
app.add_exception_handler(Exception, global_exception_handler)

# Routes
app.include_router(health.router, tags=["Health"])
app.include_router(images.router)
app.include_router(user_images.router)
app.include_router(generate.router)
