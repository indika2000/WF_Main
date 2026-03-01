import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import close_db, connect_db, init_indexes
from app.providers.factory import provider_factory
from app.routes import chat, generate, health, providers
from shared.python.middleware import RequestLoggingMiddleware, global_exception_handler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(settings.service_name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle — connect MongoDB, init providers."""
    logger.info("Starting %s service...", settings.service_name)
    client, db = await connect_db()
    app.state.db = db
    app.state.mongo_client = client
    await init_indexes(db)
    provider_factory.initialize()
    logger.info("LLM service ready")
    yield
    await close_db(client)
    logger.info("Disconnected from MongoDB")


app = FastAPI(
    title="LLM Service",
    description="Multi-provider AI text and image generation",
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
app.add_middleware(RequestLoggingMiddleware, service_name="LLM")

# Exception handler
app.add_exception_handler(Exception, global_exception_handler)

# Routes
app.include_router(health.router, tags=["Health"])
app.include_router(generate.router, tags=["Generation"])
app.include_router(chat.router, tags=["Chat"])
app.include_router(providers.router, tags=["Providers"])
