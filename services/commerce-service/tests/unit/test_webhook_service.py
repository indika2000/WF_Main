import pytest

from app.services import webhook_service


@pytest.mark.asyncio
class TestWebhookService:
    async def test_handle_unknown_event(self, test_db):
        event = {"type": "unknown.event", "data": {"object": {}}}
        # Should not raise
        await webhook_service.handle_event(event, test_db)

    async def test_payment_succeeded(self, test_db):
        # Insert a pending order
        await test_db.orders.insert_one(
            {
                "order_id": "ORD-TEST-001",
                "user_id": "user1",
                "stripe_payment_intent_id": "pi_123",
                "status": "pending",
            }
        )

        event = {
            "type": "payment_intent.succeeded",
            "data": {"object": {"id": "pi_123"}},
        }
        await webhook_service.handle_event(event, test_db)

        order = await test_db.orders.find_one({"order_id": "ORD-TEST-001"})
        assert order["status"] == "confirmed"

    async def test_payment_failed(self, test_db):
        await test_db.orders.insert_one(
            {
                "order_id": "ORD-TEST-002",
                "user_id": "user1",
                "stripe_payment_intent_id": "pi_456",
                "status": "pending",
            }
        )

        event = {
            "type": "payment_intent.payment_failed",
            "data": {"object": {"id": "pi_456"}},
        }
        await webhook_service.handle_event(event, test_db)

        order = await test_db.orders.find_one({"order_id": "ORD-TEST-002"})
        assert order["status"] == "failed"

    async def test_subscription_created(self, test_db, monkeypatch):
        # Mock permissions sync
        synced = []
        monkeypatch.setattr(
            webhook_service,
            "_sync_permissions_from_webhook",
            lambda uid, tier: synced.append((uid, tier)) or _async_noop(),
        )

        # Create a profile so the subscription can find the user
        await test_db.commerce_profiles.insert_one(
            {"user_id": "user1", "stripe_customer_id": "cus_123"}
        )

        event = {
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_123",
                    "customer": "cus_123",
                    "status": "active",
                    "current_period_start": 1700000000,
                    "current_period_end": 1702592000,
                    "cancel_at_period_end": False,
                    "metadata": {"tier": "premium"},
                    "items": {"data": []},
                }
            },
        }
        await webhook_service.handle_event(event, test_db)

        record = await test_db.subscription_records.find_one({"user_id": "user1"})
        assert record is not None
        assert record["tier"] == "premium"
        assert record["stripe_subscription_id"] == "sub_123"

        # Order should be created
        order = await test_db.orders.find_one({"user_id": "user1"})
        assert order is not None
        assert order["order_type"] == "subscription"

    async def test_subscription_deleted(self, test_db, monkeypatch):
        synced = []
        monkeypatch.setattr(
            webhook_service,
            "_sync_permissions_from_webhook",
            lambda uid, tier: synced.append((uid, tier)) or _async_noop(),
        )

        await test_db.subscription_records.insert_one(
            {
                "user_id": "user1",
                "stripe_subscription_id": "sub_789",
                "status": "active",
                "tier": "premium",
            }
        )

        event = {
            "type": "customer.subscription.deleted",
            "data": {"object": {"id": "sub_789"}},
        }
        await webhook_service.handle_event(event, test_db)

        record = await test_db.subscription_records.find_one({"user_id": "user1"})
        assert record["status"] == "expired"

    async def test_invoice_failed(self, test_db):
        await test_db.subscription_records.insert_one(
            {
                "user_id": "user1",
                "stripe_subscription_id": "sub_inv",
                "status": "active",
            }
        )

        event = {
            "type": "invoice.payment_failed",
            "data": {"object": {"subscription": "sub_inv"}},
        }
        await webhook_service.handle_event(event, test_db)

        record = await test_db.subscription_records.find_one(
            {"stripe_subscription_id": "sub_inv"}
        )
        assert record["status"] == "past_due"


async def _async_noop():
    """No-op async function for mocking."""
    pass
