# Stripe Testing Guide

## Test Cards

| Card Number | Behavior |
|-------------|----------|
| `4242 4242 4242 4242` | Succeeds |
| `4000 0000 0000 0002` | Declines |
| `4000 0025 0000 3155` | Requires 3D Secure authentication |
| `4000 0000 0000 9995` | Insufficient funds |

- **Expiry:** Any future date (e.g., 12/34)
- **CVC:** Any 3 digits (e.g., 123)
- **ZIP:** Any 5 digits (e.g., 12345)

## Testing Approaches

### 1. Dev Tools Tab (In-App)

The mobile app has a **Dev Tools** tab (visible only in development mode) with:

- **Cart Tester** — Add test items, view cart, clear cart
- **Checkout Tester** — Validate cart, create payment, confirm payment
- **Subscription Tester** — Create/cancel/view subscriptions
- **Webhook Simulator** — Fire simulated Stripe events directly (bypasses signature verification)
- **State Viewer** — Check permissions, orders, and profile in real-time

The webhook simulator calls `POST /commerce/dev/simulate-webhook` which invokes the webhook handler directly without going through Stripe. This is the fastest way to test webhook-driven flows.

### 2. Stripe CLI (Real Webhook Events)

The Stripe CLI forwards real webhook events from Stripe to your local service.

#### Setup

```bash
# Install (macOS)
brew install stripe/stripe-cli/stripe

# Install (Windows — download from https://stripe.com/docs/stripe-cli)

# Login to your Stripe account
stripe login
```

#### Forward Webhooks

```bash
# Forward events to your local Commerce Service
stripe listen --forward-to localhost:3004/webhooks/stripe

# Output will show a signing secret:
# > Ready! Your webhook signing secret is whsec_xxxxx
```

Copy the `whsec_xxxxx` signing secret and set it in `services/.env`:

```env
STRIPE_WEBHOOK_SECRET=whsec_xxxxx
```

Then restart the commerce service: `docker-compose up -d commerce`

#### Trigger Test Events

```bash
# In a separate terminal:
stripe trigger payment_intent.succeeded
stripe trigger payment_intent.payment_failed
stripe trigger customer.subscription.created
stripe trigger customer.subscription.updated
stripe trigger customer.subscription.deleted
stripe trigger invoice.payment_succeeded
stripe trigger invoice.payment_failed
```

### 3. Stripe Dashboard

1. Go to [dashboard.stripe.com](https://dashboard.stripe.com) (make sure you're in **Test mode**)
2. Navigate to **Developers > Webhooks**
3. Add an endpoint pointing to your service (requires a public URL — use ngrok for local dev)
4. Use the **Send test event** feature to trigger specific events

## Commerce Service Endpoints

### Direct (port 3004)
```bash
# Health check
curl http://localhost:3004/health

# Cart operations (requires X-Api-Key header)
curl http://localhost:3004/cart/test-user \
  -H "X-Api-Key: wf-dev-internal-api-key-2026"

# Add item to cart
curl -X POST http://localhost:3004/cart/test-user/items \
  -H "X-Api-Key: wf-dev-internal-api-key-2026" \
  -H "Content-Type: application/json" \
  -d '{"item_id":"pack-001","item_type":"pack","name":"Starter Pack","quantity":1,"unit_price":4.99}'

# Dev webhook simulation
curl -X POST http://localhost:3004/dev/simulate-webhook \
  -H "X-Api-Key: wf-dev-internal-api-key-2026" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"payment_intent.succeeded","user_id":"test-user"}'
```

### Via Gateway (port 3000)
```bash
# Same operations through the gateway (requires JWT auth)
curl http://localhost:3000/api/commerce/cart/test-user \
  -H "Authorization: Bearer dev-bypass"

curl -X POST http://localhost:3000/api/commerce/dev/simulate-webhook \
  -H "Authorization: Bearer dev-bypass" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"payment_intent.succeeded","user_id":"dev-user"}'
```

## Webhook Event Flow

```
Stripe (or simulator)
  │
  ├─ payment_intent.succeeded    → Updates order status to "confirmed"
  ├─ payment_intent.payment_failed → Updates order status to "failed"
  ├─ customer.subscription.created → Creates subscription record, syncs permissions
  ├─ customer.subscription.updated → Updates subscription record, re-syncs permissions
  ├─ customer.subscription.deleted → Marks subscription expired, downgrades to free
  ├─ invoice.payment_succeeded   → Logs event (subscription.updated handles details)
  └─ invoice.payment_failed      → Sets subscription status to "past_due"
```

## Setting Up Real Stripe Test Keys

1. Go to [dashboard.stripe.com](https://dashboard.stripe.com)
2. Make sure **Test mode** is enabled (toggle in top right)
3. Go to **Developers > API keys**
4. Copy the **Secret key** (starts with `sk_test_`)
5. Create test Products and Prices in **Products** section
6. Update `services/.env`:

```env
STRIPE_SECRET_KEY=sk_test_your_real_key
STRIPE_WEBHOOK_SECRET=whsec_from_stripe_cli
STRIPE_PRICE_PREMIUM=price_your_premium_price_id
STRIPE_PRICE_ULTRA=price_your_ultra_price_id
```

7. Restart services: `docker-compose up -d commerce`

## Running Backend Tests

```bash
cd services

# All tests
./run-tests.sh

# Commerce tests only
./run-tests.sh --service commerce

# Unit tests only
./run-tests.sh --unit

# With coverage
./run-tests.sh --coverage
```

Tests use mocked Stripe API calls (via monkeypatch) — no real Stripe account needed.
