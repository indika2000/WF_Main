# Permissions Service - System Guide

## Overview

The Permissions Service is the authoritative source of truth for user roles, feature entitlements, subscription state, and metered usage across the platform. It is a standalone FastAPI service on **port 5003** backed by **MongoDB**. It does not call other services; other services call it.

---

## Data Models

### UserPermissions

**MongoDB collection:** `user_permissions`

| Field | Type | Notes |
|-------|------|-------|
| `user_id` | string | Unique index — primary lookup key |
| `email` | string | Optional |
| `role` | string | Default: `"user"` |
| `is_premium` | bool | True for premium and ultra tiers |
| `is_admin` | bool | True when role is `"admin"` |
| `permissions.ad_free` | bool | Default: `false` |
| `permissions.premium_features` | bool | Default: `false` |
| `permissions.ai_text_generation` | bool | Default: `false` |
| `permissions.ai_image_generation` | bool | Default: `false` |
| `permissions.advanced_search` | bool | Default: `false` |
| `permissions.unlimited_storage` | bool | Default: `false` |
| `permissions.priority_support` | bool | Default: `false` |
| `created_at` | datetime | Set on insert |
| `updated_at` | datetime | Updated on every write |

All seven permission flags default to `false` at creation. The free tier grants only `ai_text_generation`.

---

### Subscription

**MongoDB collection:** `subscriptions`

| Field | Type | Notes |
|-------|------|-------|
| `user_id` | string | Unique index |
| `tier` | string | `free` / `premium` / `ultra` |
| `status` | string | `active` / `cancelled` / `expired` / `past_due` |
| `stripe_subscription_id` | string | Sparse unique index — see Gotcha section |
| `stripe_customer_id` | string | Optional |
| `current_period_start` | datetime | Billing period start |
| `current_period_end` | datetime | Billing period end |
| `cancel_at_period_end` | bool | Whether cancellation is scheduled |
| `created_at` | datetime | Set on insert |
| `updated_at` | datetime | Updated on every write |

---

### FeatureUsage

**MongoDB collection:** `feature_usage`

| Field | Type | Notes |
|-------|------|-------|
| `user_id` | string | Part of compound unique index |
| `feature` | string | Part of compound unique index (e.g. `ai_text_generation`) |
| `used` | int | Count of uses in the current period |
| `limit` | int | Hard cap for the period; `-1` means unlimited |
| `bonus` | int | Extra uses granted on top of the base limit |
| `period_start` | datetime | Start of the current 30-day rolling window |
| `period_end` | datetime | End of the current 30-day rolling window |
| `last_used_at` | datetime | Timestamp of most recent usage increment |

---

## Business Logic

### User Creation Flow

When `POST /permissions/{user_id}` is called:

1. A `UserPermissions` document is created with free-tier defaults (only `ai_text_generation: true`, all others `false`).
2. A `Subscription` record is automatically created with `tier: "free"` and `status: "active"`.
3. `FeatureUsage` records are automatically initialized for all metered features:
   - `ai_text_generation`: `limit: 10`, `used: 0`, `bonus: 0`
   - `ai_image_generation`: `limit: 0`, `used: 0`, `bonus: 0`

This ensures every new user has a complete, consistent entitlement record from the moment they are registered.

---

### Tier Sync (`sync_permissions_to_tier`)

Tier sync is the mechanism that translates a subscription tier into concrete permission flags and usage limits. It is called in two situations:

- When `POST /subscriptions/{user_id}` creates or upserts a subscription.
- When `POST /subscriptions/{user_id}/sync` is called explicitly (e.g., after a Stripe webhook is processed).

**What tier sync does:**

1. Issues a bulk MongoDB `$set` on the `user_permissions` document, writing all seven permission flags according to the tier configuration.
2. Updates `is_premium` to `true` for `premium` and `ultra` tiers, `false` for `free`.
3. Updates the `limit` field on all `feature_usage` documents for that user according to the tier's metered limits.

**Tier permission matrix applied during sync:**

| Permission | free | premium | ultra |
|------------|------|---------|-------|
| `ad_free` | false | true | true |
| `premium_features` | false | true | true |
| `ai_text_generation` | true | true | true |
| `ai_image_generation` | false | true | true |
| `advanced_search` | false | true | true |
| `unlimited_storage` | false | false | true |
| `priority_support` | false | false | true |

**Metered limits applied during sync:**

| Feature | free | premium | ultra |
|---------|------|---------|-------|
| `ai_text_generation` | 10 / month | 100 / month | -1 (unlimited) |
| `ai_image_generation` | 0 / month | 25 / month | -1 (unlimited) |

---

### Usage Checking (`check_usage`)

Called via `POST /usage/{user_id}/{feature}/check`. Returns a structured object indicating whether the user is allowed to perform the action.

**Logic:**

1. If `period_end` has passed, auto-reset the usage record: set `used = 0`, compute a new 30-day `period_start` and `period_end`.
2. Compute `effective_limit = limit + bonus`.
3. If `effective_limit == -1`, the feature is unlimited — always return `allowed: true`.
4. If `used < effective_limit`, return `allowed: true`.
5. Otherwise return `allowed: false` with a `reason` string.

**Response shape:**

```json
{
  "allowed": true,
  "used": 4,
  "limit": 10,
  "bonus": 0,
  "remaining": 6,
  "reason": null
}
```

When denied, `allowed` is `false` and `reason` contains a human-readable explanation.

---

## MongoDB Indexes

| Collection | Index | Type |
|------------|-------|------|
| `user_permissions` | `user_id` | Unique |
| `user_permissions` | `role` | Standard |
| `user_permissions` | `is_premium` | Standard |
| `subscriptions` | `user_id` | Unique |
| `subscriptions` | `stripe_subscription_id` | Sparse unique |
| `subscriptions` | `status` | Standard |
| `subscriptions` | `tier` | Standard |
| `feature_usage` | `(user_id, feature)` | Compound unique |
| `feature_usage` | `period_end` | Standard |

---

## Integration Points

| Caller | Endpoint Called | When |
|--------|----------------|------|
| **Gateway** | `GET /permissions/{user_id}`, `GET /subscriptions/{user_id}` | During token exchange to attach permissions to the session |
| **Commerce Service** | `POST /subscriptions/{user_id}` | On Stripe subscription events (creation, upgrade, downgrade, cancellation) |

This service is **standalone** — it does not make outbound calls to any other service.

---

## Key Gotcha: MongoDB Sparse Unique Index on `stripe_subscription_id`

The `subscriptions` collection has a **sparse unique** index on `stripe_subscription_id`. Sparse indexes skip documents where the indexed field is entirely absent, but they do **not** skip documents where the field is explicitly set to `null`.

If you insert a document with `stripe_subscription_id: null`, MongoDB will treat `null` as a real value for uniqueness purposes. A second insert with `null` will raise a `DuplicateKeyError` even though no real Stripe ID is involved.

**Solution:** Always use `model_dump(exclude_none=True)` when building the insert document. This omits the field entirely when it has no value, rather than writing `null`, which keeps the sparse index behaving correctly.

```python
# Correct
doc = subscription.model_dump(exclude_none=True)
await collection.insert_one(doc)

# Incorrect — will cause DuplicateKeyError on second null-id user
doc = subscription.model_dump()
await collection.insert_one(doc)
```

---

## File Structure

```
permissions-service/
├── Dockerfile
├── requirements.txt
├── app/
│   ├── main.py                      # FastAPI app with lifespan, routes, middleware
│   ├── config.py                    # PermissionsConfig extends BaseServiceConfig
│   ├── database.py                  # MongoDB connection + index creation
│   ├── models/
│   │   ├── permissions.py           # UserPermissions, DEFAULT_PERMISSIONS
│   │   ├── subscriptions.py         # Subscription, SUBSCRIPTION_TIERS
│   │   └── usage.py                 # FeatureUsage
│   ├── routes/
│   │   ├── health.py                # /health, /health/detailed
│   │   ├── permissions.py           # CRUD for permissions
│   │   ├── subscriptions.py         # CRUD + sync for subscriptions
│   │   ├── usage.py                 # Usage check / record / bonus / reset
│   │   └── admin.py                 # Admin user management
│   └── services/
│       ├── permission_service.py    # create / get / update / check + sync logic
│       ├── subscription_service.py  # create / get / upsert + tier sync
│       └── usage_service.py         # check / record / bonus / reset logic
└── tests/
    ├── conftest.py
    ├── unit/
    │   ├── test_models.py
    │   └── test_services.py
    └── integration/
        ├── test_permissions_routes.py
        ├── test_subscription_routes.py
        └── test_usage_routes.py
```

---

## Service Responsibilities by Module

### `app/main.py`
Bootstraps the FastAPI application. Registers all routers, configures CORS and authentication middleware, and manages the lifespan context (database connection open/close).

### `app/config.py`
Reads environment variables and exposes them as a typed config object. Extends a shared `BaseServiceConfig` from the platform's common library.

### `app/database.py`
Establishes the MongoDB connection on startup and ensures all indexes defined in the Indexes section above are created. Index creation is idempotent.

### `app/models/`
Pure Pydantic models with no business logic. `DEFAULT_PERMISSIONS` is a constant dict used to stamp free-tier defaults. `SUBSCRIPTION_TIERS` is a dict keyed by tier name containing the permission flags and usage limits for that tier.

### `app/routes/`
Thin FastAPI route handlers. Each handler validates the incoming request, calls the appropriate service method, and returns the response. No business logic lives here.

### `app/services/`
All business logic lives in the service layer. Services interact with MongoDB directly via the database module. The three services map cleanly to the three data models.
