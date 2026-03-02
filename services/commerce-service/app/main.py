import logging
from contextlib import asynccontextmanager

import stripe
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import close_db, close_redis, connect_db, connect_redis, init_indexes
from app.routes import cart, checkout, health, orders, profile, subscriptions, webhooks
from shared.python.middleware import RequestLoggingMiddleware, global_exception_handler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(settings.service_name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle — MongoDB, Redis, Stripe."""
    logger.info("Starting %s service...", settings.service_name)

    # MongoDB
    client, db = await connect_db()
    app.state.db = db
    app.state.mongo_client = client
    await init_indexes(db)
    logger.info("Connected to MongoDB, indexes created")

    # Redis
    r = await connect_redis()
    app.state.redis = r
    logger.info("Connected to Redis")

    # Stripe
    stripe.api_key = settings.stripe_secret_key
    if settings.stripe_secret_key:
        logger.info("Stripe API key configured")
    else:
        logger.warning("Stripe API key not set — payment operations will fail")

    yield

    await close_redis(r)
    logger.info("Disconnected from Redis")
    await close_db(client)
    logger.info("Disconnected from MongoDB")


app = FastAPI(
    title="Commerce Service",
    description="Payments, subscriptions, cart, and order management via Stripe",
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
app.add_middleware(RequestLoggingMiddleware, service_name="COMMERCE")

# Exception handler
app.add_exception_handler(Exception, global_exception_handler)

# Routes
app.include_router(health.router, tags=["Health"])
app.include_router(cart.router, tags=["Cart"])
app.include_router(checkout.router, tags=["Checkout"])
app.include_router(subscriptions.router, tags=["Subscriptions"])
app.include_router(orders.router, tags=["Orders"])
app.include_router(profile.router, tags=["Profile"])
app.include_router(webhooks.router, tags=["Webhooks"])
