import logging

import stripe
from fastapi import APIRouter, Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.database import get_db
from app.services import webhook_service
from shared.python.responses import error_response, success_response

logger = logging.getLogger("commerce")

router = APIRouter(prefix="/webhooks")


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Handle Stripe webhook events.

    NO auth dependency — Stripe calls this directly.
    Authentication is via Stripe signature verification.
    Must read raw body (no Pydantic model) for signature verification.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not settings.stripe_webhook_secret:
        logger.warning("Stripe webhook secret not configured")
        return error_response(
            message="Webhook not configured",
            error_code="NOT_CONFIGURED",
            status_code=500,
        )

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        logger.warning("Invalid webhook payload")
        return error_response(
            message="Invalid payload",
            error_code="INVALID_PAYLOAD",
            status_code=400,
        )
    except stripe.SignatureVerificationError:
        logger.warning("Invalid Stripe signature")
        return error_response(
            message="Invalid signature",
            error_code="INVALID_SIGNATURE",
            status_code=400,
        )

    await webhook_service.handle_event(event, db)
    return success_response(message="Webhook processed")
