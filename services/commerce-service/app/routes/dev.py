"""
Dev-only endpoints for testing webhook flows and Stripe simulation.
Only available when settings.debug is True (NODE_ENV=development).
"""

import time
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import settings
from app.database import get_db, get_redis
from app.services import webhook_service
from shared.python.auth import verify_api_key
from shared.python.responses import success_response, error_response

logger = logging.getLogger("commerce.dev")

router = APIRouter(prefix="/dev", tags=["Dev Tools"])


class SimulateWebhookRequest(BaseModel):
    event_type: str
    user_id: str | None = None
    overrides: dict | None = None


# Sample event payloads matching Stripe's format
def _sample_events() -> dict:
    now = int(time.time())
    return {
        "payment_intent.succeeded": {
            "id": "pi_test_simulated",
            "object": "payment_intent",
            "status": "succeeded",
            "amount": 999,
            "currency": "usd",
        },
        "payment_intent.payment_failed": {
            "id": "pi_test_simulated",
            "object": "payment_intent",
            "status": "requires_payment_method",
            "amount": 999,
            "currency": "usd",
        },
        "customer.subscription.created": {
            "id": "sub_test_simulated",
            "object": "subscription",
            "customer": None,  # Filled from user profile
            "status": "active",
            "metadata": {"tier": "premium"},
            "current_period_start": now,
            "current_period_end": now + 2592000,  # 30 days
            "cancel_at_period_end": False,
            "items": {"data": []},
        },
        "customer.subscription.updated": {
            "id": "sub_test_simulated",
            "object": "subscription",
            "customer": None,
            "status": "active",
            "metadata": {"tier": "premium"},
            "current_period_start": now,
            "current_period_end": now + 2592000,
            "cancel_at_period_end": False,
            "items": {"data": []},
        },
        "customer.subscription.deleted": {
            "id": "sub_test_simulated",
            "object": "subscription",
            "customer": None,
            "status": "canceled",
            "metadata": {"tier": "premium"},
            "current_period_start": now,
            "current_period_end": now,
            "cancel_at_period_end": False,
            "items": {"data": []},
        },
        "invoice.payment_succeeded": {
            "id": "in_test_simulated",
            "object": "invoice",
            "subscription": "sub_test_simulated",
            "status": "paid",
        },
        "invoice.payment_failed": {
            "id": "in_test_simulated",
            "object": "invoice",
            "subscription": "sub_test_simulated",
            "status": "open",
        },
    }


SUPPORTED_EVENTS = list(_sample_events().keys())


@router.post("/simulate-webhook")
async def simulate_webhook(
    body: SimulateWebhookRequest,
    user=Depends(verify_api_key),
    db=Depends(get_db),
):
    """Simulate a Stripe webhook event (dev only). Bypasses signature verification."""
    if not settings.debug:
        return error_response("Only available in development mode", "DEV_ONLY", 403)

    if body.event_type not in _sample_events():
        return error_response(
            f"Unknown event type. Supported: {SUPPORTED_EVENTS}",
            "INVALID_EVENT_TYPE",
            400,
        )

    event_data = _sample_events()[body.event_type].copy()

    # Fill customer ID from the user's commerce profile if available
    if body.user_id:
        profile = await db.commerce_profiles.find_one({"user_id": body.user_id})
        if profile and "customer" in event_data:
            event_data["customer"] = profile.get("stripe_customer_id", "cus_test_sim")

    # Apply any overrides from the request
    if body.overrides:
        event_data.update(body.overrides)

    event = {"type": body.event_type, "data": {"object": event_data}}

    logger.info("[DEV] Simulating webhook: %s", body.event_type)
    await webhook_service.handle_event(event, db)

    return success_response(
        data={"event_type": body.event_type, "simulated": True},
        message=f"Simulated {body.event_type} successfully",
    )


@router.get("/webhook-events")
async def list_webhook_events(user=Depends(verify_api_key)):
    """List all supported webhook event types for simulation."""
    if not settings.debug:
        return error_response("Only available in development mode", "DEV_ONLY", 403)

    return success_response(data={"events": SUPPORTED_EVENTS})
