import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import close_db, connect_db, init_indexes
from app.routes import collection, creatures, generate, health, supply
from shared.python.middleware import RequestLoggingMiddleware, global_exception_handler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(settings.service_name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle — MongoDB + generation config."""
    logger.info("Starting %s service...", settings.service_name)

    # MongoDB
    client, db = await connect_db()
    app.state.db = db
    app.state.mongo_client = client
    await init_indexes(db)
    logger.info("Connected to MongoDB, indexes created")

    # Load generation config
    from app.services.config_loader import load_config

    config = load_config(settings.generation_config_path)
    app.state.generation_config = config
    logger.info(
        "Loaded generation config %s: %d biomes, %d species",
        config.version,
        len(config.biomes),
        len(config._species_ids),
    )

    yield

    await close_db(client)
    logger.info("Disconnected from MongoDB")


app = FastAPI(
    title="Character Service",
    description="Deterministic creature generation from barcode scans",
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
app.add_middleware(RequestLoggingMiddleware, service_name="CHARACTER")

# Exception handler
app.add_exception_handler(Exception, global_exception_handler)

# Routes
app.include_router(health.router, tags=["Health"])
app.include_router(generate.router, tags=["Generate"])
app.include_router(creatures.router, tags=["Creatures"])
app.include_router(collection.router, tags=["Collection"])
app.include_router(supply.router, tags=["Supply"])

# Dev tools — only in development mode
if settings.debug:
    from app.routes import dev

    app.include_router(dev.router, tags=["Dev Tools"])
