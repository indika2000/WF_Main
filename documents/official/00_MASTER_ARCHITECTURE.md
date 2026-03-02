# WildernessFriends — Master Architecture Guide

## 1. System Overview

WildernessFriends is a collectible wildlife card mobile app built on a microservices backend. The mobile app (React Native + Expo) communicates exclusively through a Node.js API Gateway, which proxies requests to four Python FastAPI backend services. All services run in Docker with hot-reload for development.

```
┌─────────────────────────────────────────────────────────┐
│              React Native App (Expo SDK 52)              │
│                                                          │
│  Firebase Auth ──→ ID Token ──→ Gateway JWT Exchange     │
│  SDK Layer (Axios) ──→ All subsequent API requests       │
└──────────────────────────┬───────────────────────────────┘
                           │ HTTPS (Bearer JWT)
                           ▼
┌─────────────────────────────────────────────────────────┐
│              Node.js API Gateway (:3000)                  │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────────┐ │
│  │  Auth    │  │  Rate    │  │  Proxy + Internal JWT  │ │
│  │  Verify  │→ │  Limit   │→ │  Injection             │ │
│  └──────────┘  └──────────┘  └────────────────────────┘ │
└────┬──────────┬──────────┬──────────┬────────────────────┘
     │          │          │          │  Internal JWT + X-Api-Key
     ▼          ▼          ▼          ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│ Perms   │ │Commerce │ │ Image   │ │  LLM    │
│ Service │ │ Service │ │ Service │ │ Service │
│ :5003   │ │ :3004   │ │ :5001   │ │ :5000   │
│ FastAPI │ │ FastAPI │ │ FastAPI │ │ FastAPI │
└────┬────┘ └──┬───┬──┘ └────┬────┘ └────┬────┘
     │         │   │         │            │
     ▼         ▼   ▼         ▼            ▼
┌─────────────────────────────────────────────────────────┐
│                     Data Layer                           │
│  ┌───────────┐  ┌───────────┐  ┌──────────────────────┐ │
│  │  MongoDB  │  │   Redis   │  │  File Storage        │ │
│  │  :27017   │  │   :6379   │  │  (Local / S3-ready)  │ │
│  └───────────┘  └───────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## 2. Service Map

| Service | Port | Language | Framework | Database | Dockerfile |
|---------|------|----------|-----------|----------|------------|
| **Gateway** | 3000 | Node.js 20 | Express 4.21 | — | `node-gateway/Dockerfile` |
| **Permissions** | 5003 | Python 3.12 | FastAPI | MongoDB | `permissions-service/Dockerfile` |
| **Commerce** | 3004 | Python 3.12 | FastAPI | MongoDB + Redis | `commerce-service/Dockerfile` |
| **Image** | 5001 | Python 3.12 | FastAPI | MongoDB + Local FS | `image-service/Dockerfile` |
| **LLM** | 5000 | Python 3.12 | FastAPI | MongoDB | `llm-service/Dockerfile` |
| **MongoDB** | 27017 | — | — | — | `mongo:7.0` |
| **Redis** | 6379 | — | — | — | `redis:7-alpine` |

## 3. Service Dependencies

```
Permissions Service  ← standalone (no service deps)
LLM Service          ← standalone (external AI provider APIs only)
Image Service        ← depends on: LLM Service (AI image generation proxy)
Commerce Service     ← depends on: Permissions Service (tier sync on subscription events)
Node Gateway         ← depends on: ALL services (proxy layer)
```

## 4. Authentication Flow

The system uses a two-layer token architecture:

```
Step 1: Login (one-time)
═══════════════════════
Mobile App
    │
    ├─ Firebase Auth (email/password) → Firebase ID Token
    │
    ├─ POST /api/auth/token (Bearer: Firebase ID Token)
    │       │
    │       ├─ Gateway verifies Firebase ID token via Admin SDK
    │       ├─ Fetches user permissions from Permissions Service
    │       ├─ Auto-creates user if first login (404 → POST)
    │       ├─ Fetches subscription info
    │       ├─ Signs internal JWT (HS256, 1hr expiry)
    │       │   Payload: { uid, email, role, is_premium, permissions, subscription_tier }
    │       │
    │       └─ Returns: { token: <JWT>, user: { role, permissions, subscription } }
    │
    └─ Mobile caches JWT in memory (tokenManager.ts)

Step 2: All subsequent requests
═══════════════════════════════
Mobile App
    │
    ├─ Axios interceptor attaches: Authorization: Bearer <internal JWT>
    │
    ├─ Gateway auth middleware:
    │   1. Tries verifyToken(jwt) — HS256 local verification (fast path)
    │   2. If valid: sets req.user, req.internalToken, req.permissions
    │   3. Permissions middleware: skips (req.internalToken already set)
    │   4. Proxy injects: Authorization + X-Api-Key headers → backend service
    │
    └─ Backend service:
        ├─ shared/python/auth.py verifies JWT or X-Api-Key
        └─ Returns response in { success, data, message } envelope

Step 3: Token refresh (transparent)
════════════════════════════════════
    ├─ tokenManager checks expiry with 60s buffer before each request
    ├─ On expiry: re-calls exchangeToken() (Step 1 again)
    ├─ On 401: Axios interceptor calls refreshToken(), retries once
    └─ On logout: clearToken() wipes cached JWT
```

## 5. Standardized Response Format

All services use this envelope:

```json
// Success
{
  "success": true,
  "message": "Operation completed",
  "data": { ... }
}

// Error
{
  "success": false,
  "message": "Human-readable error",
  "error_code": "SCREAMING_SNAKE_CASE",
  "detail": "Optional extra context"
}
```

The mobile SDK's Axios interceptor auto-unwraps `data`, so SDK functions return the inner object directly.

### HTTP Status Codes

| Code | Usage |
|------|-------|
| 200 | Success |
| 201 | Created (new resource) |
| 400 | Validation error / bad request |
| 401 | Not authenticated |
| 403 | Not authorized (permission denied) |
| 404 | Not found |
| 409 | Conflict (duplicate) |
| 429 | Rate limited |
| 500 | Internal server error |
| 503 | Service unavailable (proxy error) |

## 6. Gateway Proxy Route Map

| Gateway Path | Backend Service | Backend Path | Auth Required |
|---|---|---|---|
| `POST /api/auth/token` | Gateway (local) | — | Firebase token |
| `GET /api/auth/verify` | Gateway (local) | — | Internal JWT |
| `GET /health` | Gateway (local) | — | No |
| `GET /health/services` | Gateway (local) | — | No |
| `/api/permissions/**` | Permissions :5003 | `/permissions/**` | Yes |
| `/api/commerce/**` | Commerce :3004 | `/**` | Yes |
| `/api/commerce/webhooks/**` | Commerce :3004 | `/webhooks/**` | No (Stripe signature) |
| `/api/images/**` | Image :5001 | `/images/**` | Yes |
| `/api/llm/**` | LLM :5000 | `/**` | Yes |
| `/api/chat/**` | LLM :5000 | `/chat/**` | Yes |

## 7. How to Add a New Backend Service

### Checklist

1. **Create service directory**: `services/new-service/`
2. **Dockerfile**: Copy from an existing Python service; adjust `COPY` paths
3. **requirements.txt**: Include `fastapi`, `uvicorn`, `motor`, plus service-specific deps
4. **app/main.py**: FastAPI app with lifespan (DB connection), mount shared middleware
5. **app/config.py**: Extend `BaseServiceConfig` from `shared.python.config`
6. **app/routes/**: Define route files with endpoint handlers
7. **app/models/**: Pydantic models for request/response validation
8. **app/services/**: Business logic layer
9. **docker-compose.yml**: Add service entry with:
   - `build: { context: ., dockerfile: new-service/Dockerfile }`
   - Port mapping, environment variables, dependencies
   - `PYTHONPATH: /app` in environment
10. **docker-compose.dev.yml**: Add dev overrides:
    - Volume mounts: `./new-service/app:/app/app`, `./shared:/app/shared`, `./new-service/tests:/app/tests`, `./pytest.ini:/app/pytest.ini`
    - Command: `uvicorn app.main:app --host 0.0.0.0 --port XXXX --reload`
    - Expose port to host
11. **Gateway config**: Add entry to `services/node-gateway/src/config/services.js`
12. **Gateway proxy route**: Add to `services/node-gateway/src/routes/proxy.js`
13. **Mobile SDK module**: Create `WildernessFriends/services/newService.ts`
14. **Tests**: Create `tests/unit/` and `tests/integration/` with conftest.py
15. **Update run-tests.sh**: Add the new service to `PYTHON_SERVICES`
16. **Documentation**: Add `documents/official/new-service/` with QUICK_REFERENCE.md and SYSTEM_GUIDE.md

### Key Rules for New Services

- Use `context: .` (services root) as Docker build context — NOT the service directory
- Set `PYTHONPATH=/app` in the Dockerfile
- Import shared utilities as `from shared.python.auth import ...`
- Use `success_response()` / `error_response()` from shared — never raw JSONResponse with datetime
- Define static routes before parameterized routes in FastAPI routers
- All auth goes through `get_current_user` dependency from `shared.python.auth`

## 8. Environment Variable Reference

### Gateway (Node.js)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NODE_ENV` | No | `development` | Environment mode |
| `GATEWAY_PORT` | No | `3000` | Server port |
| `JWT_SECRET` | **Yes** | — | HS256 signing secret (must match all services) |
| `JWT_EXPIRY` | No | `1h` | JWT lifetime |
| `INTERNAL_API_KEY` | **Yes** | — | Service-to-service API key |
| `FIREBASE_PROJECT_ID` | **Yes** | — | Firebase Admin SDK |
| `FIREBASE_CLIENT_EMAIL` | **Yes** | — | Firebase Admin SDK |
| `FIREBASE_PRIVATE_KEY` | **Yes** | — | Firebase Admin SDK (with `\n` escapes) |
| `PERMISSIONS_SERVICE_URL` | No | `http://permissions:5003` | Internal URL |
| `COMMERCE_SERVICE_URL` | No | `http://commerce:3004` | Internal URL |
| `IMAGE_SERVICE_URL` | No | `http://image-service:5001` | Internal URL |
| `LLM_SERVICE_URL` | No | `http://llm-service:5000` | Internal URL |
| `CORS_ORIGINS` | No | `localhost:8081,localhost:19006` | Comma-separated origins |

### All Python Services (shared)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MONGODB_URI` | No | `mongodb://mongodb:27017/wildernessfriends` | MongoDB connection |
| `REDIS_URL` | No | `redis://redis:6379` | Redis connection (Commerce only) |
| `INTERNAL_API_KEY` | **Yes** | — | Must match gateway's key |
| `JWT_SECRET` | **Yes** | — | Must match gateway's key |
| `SERVICE_NAME` | No | (per service) | Logging prefix |
| `DEBUG` | No | `false` | Enables dev routes |

### LLM Service (additional)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | No | — | Enables Anthropic provider |
| `OPENAI_API_KEY` | No | — | Enables OpenAI provider |
| `GOOGLE_API_KEY` | No | — | Enables Gemini provider |
| `LLM_CONFIG_PATH` | No | `config/providers.yml` | Provider configuration |

### Commerce Service (additional)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `STRIPE_SECRET_KEY` | **Yes** | — | Stripe API key |
| `STRIPE_WEBHOOK_SECRET` | **Yes** | — | Stripe webhook signing secret |
| `STRIPE_PRICE_PREMIUM` | **Yes** | — | Stripe Price ID for premium tier |
| `STRIPE_PRICE_ULTRA` | **Yes** | — | Stripe Price ID for ultra tier |

### Image Service (additional)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `IMAGE_STORAGE_PATH` | No | `/storage` | Local storage root |
| `IMAGE_MAX_FILE_SIZE` | No | `10485760` | Max upload size (10MB) |
| `LLM_SERVICE_URL` | No | `http://llm-service:5000` | For AI generation proxy |

### Mobile App (Expo)

| Variable | Description |
|----------|-------------|
| `EXPO_PUBLIC_FIREBASE_API_KEY` | Firebase web config |
| `EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN` | Firebase web config |
| `EXPO_PUBLIC_FIREBASE_PROJECT_ID` | Firebase web config |
| `EXPO_PUBLIC_FIREBASE_STORAGE_BUCKET` | Firebase web config |
| `EXPO_PUBLIC_FIREBASE_MESSAGING_SENDER_ID` | Firebase web config |
| `EXPO_PUBLIC_FIREBASE_APP_ID` | Firebase web config |
| `EXPO_PUBLIC_API_URL` | Gateway URL (e.g., `http://192.168.x.x:3000/api`) |

## 9. Docker Commands Quick Reference

```bash
# Navigate to services directory
cd services

# Start everything (development with hot-reload)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Start in background
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Rebuild after Dockerfile or dependency changes
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# Restart a single service (does NOT reload .env changes)
docker-compose restart gateway

# Recreate a service (DOES reload .env changes)
docker-compose up -d gateway

# View logs
docker-compose logs -f commerce        # Single service
docker-compose logs -f --tail=50       # All services, last 50 lines

# Run tests
docker-compose exec -T permissions pytest tests/ -v
docker-compose exec -T gateway npx jest --verbose

# Shell into a container
docker-compose exec commerce bash
docker-compose exec gateway sh

# Stop everything (keeps data)
docker-compose down

# Stop and destroy ALL data (MongoDB, Redis, images)
docker-compose down -v              # WARNING: destroys all volumes
```

## 10. Shared Python Utilities

All Python services import from `shared.python.*`:

| Module | Key Exports | Usage |
|--------|-------------|-------|
| `shared.python.auth` | `get_current_user`, `verify_jwt`, `verify_api_key`, `require_role` | FastAPI dependency injection for auth |
| `shared.python.responses` | `success_response`, `error_response` | Standardized JSON responses with datetime handling |
| `shared.python.middleware` | `RequestLoggingMiddleware`, `global_exception_handler` | Per-request logging, 500 handler |
| `shared.python.config` | `BaseServiceConfig` | Pydantic-settings base (extend per service) |

## 11. Cross-References

| Topic | Document |
|-------|----------|
| Gotchas and workarounds | [01_LESSONS_LEARNED.md](01_LESSONS_LEARNED.md) |
| Gateway details | [gateway/SYSTEM_GUIDE.md](gateway/SYSTEM_GUIDE.md) |
| Permissions & tiers | [permissions/SYSTEM_GUIDE.md](permissions/SYSTEM_GUIDE.md) |
| Stripe & checkout | [commerce/SYSTEM_GUIDE.md](commerce/SYSTEM_GUIDE.md) |
| Image processing | [image-service/SYSTEM_GUIDE.md](image-service/SYSTEM_GUIDE.md) |
| AI providers & chat | [llm-service/SYSTEM_GUIDE.md](llm-service/SYSTEM_GUIDE.md) |
| Mobile SDK layer | [mobile-sdk/SYSTEM_GUIDE.md](mobile-sdk/SYSTEM_GUIDE.md) |
| Test suite | [testing/SYSTEM_GUIDE.md](testing/SYSTEM_GUIDE.md) |
