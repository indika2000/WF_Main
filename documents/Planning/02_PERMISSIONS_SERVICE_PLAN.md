# Permissions Service - Planning Document

## 1. Purpose

A generic entitlements and feature-gating service. It manages:
- **User permissions** — fine-grained boolean flags controlling access to features
- **Subscription tiers** — defining what each tier unlocks
- **Feature usage metering** — tracking and limiting usage of metered features (e.g., AI generations per month)
- **Role management** — user, admin, moderator roles

This service is **application-agnostic** — it doesn't know what features mean, only whether a user has permission to use them.

## 2. Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | Python 3.12 + FastAPI |
| Database | MongoDB |
| Validation | Pydantic v2 |
| Auth | Firebase token verify + internal JWT |
| Testing | pytest + httpx |

## 3. Data Models

### 3.1 UserPermissions

```python
class UserPermissions(BaseModel):
    user_id: str                    # Firebase UID
    role: str = "user"              # user | admin | moderator
    is_premium: bool = False
    is_admin: bool = False
    permissions: dict[str, bool]    # Feature flags
    created_at: datetime
    updated_at: datetime
```

**Default permission flags** (extensible — new flags added without schema migration):

```python
DEFAULT_PERMISSIONS = {
    "ad_free": False,
    "premium_features": False,
    "ai_text_generation": False,
    "ai_image_generation": False,
    "advanced_search": False,
    "unlimited_storage": False,
    "priority_support": False,
}
```

### 3.2 Subscription

```python
class Subscription(BaseModel):
    user_id: str
    tier: str                       # free | premium | ultra
    status: str                     # active | cancelled | expired | past_due
    stripe_subscription_id: str | None
    stripe_customer_id: str | None
    current_period_start: datetime | None
    current_period_end: datetime | None
    cancel_at_period_end: bool = False
    created_at: datetime
    updated_at: datetime
```

### 3.3 FeatureUsage

```python
class FeatureUsage(BaseModel):
    user_id: str
    feature: str                    # e.g., "ai_text_generation"
    used: int = 0
    limit: int                      # Monthly limit (-1 = unlimited)
    bonus: int = 0                  # Extra uses from promotions/ads
    period_start: datetime          # Start of current billing period
    period_end: datetime            # End of current billing period
    last_used_at: datetime | None
```

### 3.4 SubscriptionTier (Config)

```python
SUBSCRIPTION_TIERS = {
    "free": {
        "price": 0,
        "permissions": {
            "ad_free": False,
            "premium_features": False,
            "ai_text_generation": True,
            "ai_image_generation": False,
            "advanced_search": False,
            "unlimited_storage": False,
        },
        "feature_limits": {
            "ai_text_generation": 10,    # 10 per month
            "ai_image_generation": 0,     # Not available
        }
    },
    "premium": {
        "price": 4.99,
        "permissions": {
            "ad_free": True,
            "premium_features": True,
            "ai_text_generation": True,
            "ai_image_generation": True,
            "advanced_search": True,
            "unlimited_storage": False,
        },
        "feature_limits": {
            "ai_text_generation": 100,
            "ai_image_generation": 25,
        }
    },
    "ultra": {
        "price": 9.99,
        "permissions": {
            "ad_free": True,
            "premium_features": True,
            "ai_text_generation": True,
            "ai_image_generation": True,
            "advanced_search": True,
            "unlimited_storage": True,
        },
        "feature_limits": {
            "ai_text_generation": -1,     # Unlimited
            "ai_image_generation": -1,    # Unlimited
        }
    }
}
```

## 4. API Endpoints

### 4.1 Permissions CRUD

| Method | Path | Description |
|--------|------|-------------|
| GET | `/permissions/{user_id}` | Get user's current permissions |
| POST | `/permissions/{user_id}` | Create permissions for new user (called on first auth) |
| PATCH | `/permissions/{user_id}` | Update specific permission flags |
| GET | `/permissions/{user_id}/check/{permission}` | Quick boolean check for a specific permission |

### 4.2 Subscription Management

| Method | Path | Description |
|--------|------|-------------|
| GET | `/subscriptions/{user_id}` | Get current subscription |
| POST | `/subscriptions/{user_id}` | Create/update subscription (called by Commerce Service) |
| POST | `/subscriptions/{user_id}/sync` | Sync permissions to match current subscription tier |
| GET | `/subscriptions/tiers` | List available subscription tiers and their benefits |

### 4.3 Feature Usage Metering

| Method | Path | Description |
|--------|------|-------------|
| GET | `/usage/{user_id}/{feature}` | Get usage stats for a feature |
| POST | `/usage/{user_id}/{feature}/check` | Check if user can use feature (returns allowed + remaining) |
| POST | `/usage/{user_id}/{feature}/record` | Record one use of a feature |
| POST | `/usage/{user_id}/{feature}/bonus` | Add bonus uses (from ads, promotions) |
| POST | `/usage/reset-expired` | Reset usage counters for expired periods (cron job) |

### 4.4 Admin

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/users` | List users with filters (role, tier, etc.) |
| PATCH | `/admin/users/{user_id}/role` | Change user role |
| POST | `/admin/tiers` | Update tier definitions (hot config) |

## 5. Key Business Logic

### 5.1 Auto-Sync on Subscription Change

When a subscription is created or updated, permissions are automatically synced:

```
Commerce Service webhook → POST /subscriptions/{user_id}
    │
    ├─ Update subscription record
    ├─ Look up tier config
    ├─ Update all permission flags to match tier
    ├─ Update feature usage limits to match tier
    └─ Return updated permissions
```

### 5.2 Feature Usage Check Flow

```
Service wants to use a feature (e.g., LLM Service before generating)
    │
    POST /usage/{user_id}/ai_text_generation/check
    │
    ├─ Check permission flag: ai_text_generation == true?
    │   └─ If false → return { allowed: false, reason: "feature_disabled" }
    │
    ├─ Check usage period: is current period expired?
    │   └─ If expired → reset counter, start new period
    │
    ├─ Check limit: used < (limit + bonus)?
    │   ├─ If limit == -1 → unlimited, always allowed
    │   └─ If used >= (limit + bonus) → return { allowed: false, reason: "limit_reached" }
    │
    └─ Return { allowed: true, used: N, limit: M, remaining: M-N }
```

### 5.3 New User Initialization

When a user first authenticates:
1. Gateway calls `POST /permissions/{user_id}` with email
2. Service creates default permissions (free tier)
3. Service creates free subscription record
4. Service creates feature usage records with free tier limits

### 5.4 Bonus System

Users can earn bonus feature uses through:
- Watching ads (future)
- Referrals (future)
- Promotional events (future)
- Admin grants

Bonuses are **additive** to the tier limit and **do not roll over** between periods.

## 6. MongoDB Collections

### 6.1 Indexes

```
permissions:
  - user_id (unique)
  - role
  - is_premium

subscriptions:
  - user_id (unique)
  - stripe_subscription_id (unique, sparse)
  - status
  - tier

feature_usage:
  - (user_id, feature) compound unique
  - period_end (for cleanup queries)
```

## 7. Security

- All endpoints require valid JWT (from gateway) or API key (service-to-service)
- Users can only read their own permissions
- Only admin role can modify other users' permissions
- Subscription updates must come from Commerce Service (API key verified)
- Feature usage recording requires valid JWT with matching user_id

## 8. Error Handling

| Scenario | Status | Error Code |
|----------|--------|------------|
| User not found | 404 | USER_NOT_FOUND |
| Permission denied | 403 | PERMISSION_DENIED |
| Feature limit reached | 403 | USAGE_LIMIT_REACHED |
| Invalid tier | 400 | INVALID_TIER |
| Duplicate user | 409 | USER_EXISTS |

## 9. Integration Points

| Service | Direction | Purpose |
|---------|-----------|---------|
| Node Gateway | ← called by | Auth flow, permission checks for JWT |
| Commerce Service | ← called by | Subscription updates trigger permission sync |
| LLM Service | ← called by | Feature usage checks before AI generation |
| Image Service | ← called by | Storage quota checks |

## 10. Testing Strategy

### Unit Tests
- Permission CRUD operations
- Subscription tier sync logic
- Feature usage check/record logic
- Period expiry and reset logic
- Bonus calculation

### Integration Tests
- Full API endpoint tests with test MongoDB
- Auth middleware validation
- Subscription update → permission sync flow
- Feature usage metering across period boundaries
