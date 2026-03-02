# Commerce Service - Quick Reference

## Overview

The Commerce Service is a **FastAPI** microservice running on **port 3004**. It handles all commerce-related operations for the platform, backed by **MongoDB** (persistent data), **Redis** (cart sessions), and **Stripe** (payments and subscriptions).

**Responsibilities:**
- Shopping cart management (Redis-backed, 7-day TTL per cart)
- Checkout flow with Stripe PaymentIntents
- Order management and history
- Subscription lifecycle (create, cancel, reactivate, tier changes)
- User commerce profiles with saved addresses
- Stripe webhook processing

---

## Endpoint Reference

All endpoints except `/health`, `/health/detailed`, and `/webhooks/stripe` require authentication via **JWT** or **API Key**.

### Cart

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/cart/{user_id}` | Retrieve the current cart for a user |
| `POST` | `/cart/{user_id}/items` | Add an item to the cart |
| `PATCH` | `/cart/{user_id}/items/{item_id}` | Update quantity of a cart item |
| `DELETE` | `/cart/{user_id}/items/{item_id}` | Remove a specific item from the cart |
| `DELETE` | `/cart/{user_id}` | Clear the entire cart |

### Checkout

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/checkout/{user_id}/validate` | Validate cart is ready for checkout |
| `POST` | `/checkout/{user_id}/create-payment` | Create Stripe PaymentIntent and EphemeralKey |
| `POST` | `/checkout/{user_id}/confirm` | Confirm payment and create order record |

### Orders

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orders/{user_id}` | List orders (supports `?page=&limit=` pagination) |
| `GET` | `/orders/{user_id}/{order_id}` | Get a specific order by ID |

### Subscriptions

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/subscriptions/{user_id}` | Get active subscription record |
| `POST` | `/subscriptions/{user_id}/create` | Create a new Stripe subscription |
| `POST` | `/subscriptions/{user_id}/cancel` | Cancel subscription at period end |
| `POST` | `/subscriptions/{user_id}/reactivate` | Reactivate a pending-cancellation subscription |
| `POST` | `/subscriptions/{user_id}/change-tier` | Upgrade or downgrade subscription tier |

### Profile

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/profile/{user_id}` | Get user commerce profile |
| `POST` | `/profile/{user_id}/addresses` | Add a new address to profile |
| `PATCH` | `/profile/{user_id}/addresses/{address_id}` | Update an existing address |
| `DELETE` | `/profile/{user_id}/addresses/{address_id}` | Remove an address |

### Webhooks

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/webhooks/stripe` | Receive Stripe webhook events (no auth - signature verified) |

### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Basic liveness check |
| `GET` | `/health/detailed` | Detailed health with dependency status |

### Dev (Debug Mode Only)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/dev/simulate-webhook` | Simulate a Stripe webhook event without signature |
| `GET` | `/dev/webhook-events` | List all supported webhook event types |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `MONGODB_URI` | MongoDB connection string |
| `REDIS_URL` | Redis connection string |
| `INTERNAL_API_KEY` | API key for service-to-service auth |
| `JWT_SECRET` | Secret for verifying JWT tokens |
| `STRIPE_SECRET_KEY` | Stripe secret API key |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret |
| `STRIPE_PRICE_PREMIUM` | Stripe Price ID for the Premium tier |
| `STRIPE_PRICE_ULTRA` | Stripe Price ID for the Ultra tier |
| `PERMISSIONS_SERVICE_URL` | Base URL of the Permissions Service |
| `DEBUG` | Enables dev-only routes when `true` |

---

## Common Errors

| Code | Error | Description |
|------|-------|-------------|
| `400` | `CART_EMPTY` | Checkout attempted on an empty cart |
| `400` | `INVALID_TIER` | Subscription tier is not `premium` or `ultra` |
| `404` | `ORDER_NOT_FOUND` | No order matches the given order ID for that user |
| `404` | `SUBSCRIPTION_NOT_FOUND` | No subscription record exists for the user |
| `409` | `ACTIVE_SUBSCRIPTION_EXISTS` | User already has an active subscription |

---

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework |
| `stripe` | Stripe API client (payments, subscriptions, webhooks) |
| `motor` | Async MongoDB driver |
| `redis[hiredis]` | Redis client with hiredis C parser |
| `httpx` | Async HTTP client for Permissions Service calls |
