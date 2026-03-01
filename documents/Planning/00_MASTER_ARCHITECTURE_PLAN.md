# WildernessFriends - Master Architecture Plan

## 1. Overview

This document defines the foundational service architecture for WildernessFriends. All services are designed to be **generic and reusable** — they provide capabilities (permissions, commerce, images, AI) that any application feature can consume. Application-specific logic will be layered on top once the foundation is in place.

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                 React Native App                     │
│              (Expo Go / Dev Client)                  │
│                                                      │
│  Firebase Auth ──→ ID Token ──→ API Requests         │
└──────────────────────┬──────────────────────────────┘
                       │ HTTPS
                       ▼
┌─────────────────────────────────────────────────────┐
│              Node.js API Gateway (:3000)             │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │  Auth    │  │  Rate    │  │  Route Proxy /    │  │
│  │  Verify  │→ │  Limit   │→ │  Orchestration    │  │
│  └──────────┘  └──────────┘  └───────────────────┘  │
└────┬──────────┬──────────┬──────────┬───────────────┘
     │          │          │          │
     ▼          ▼          ▼          ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│ Perms   │ │Commerce │ │ Image   │ │  LLM    │
│ Service │ │ Service │ │ Service │ │ Service │
│ (:5003) │ │ (:3004) │ │ (:5001) │ │ (:5000) │
│ FastAPI │ │ FastAPI │ │ FastAPI │ │ FastAPI │
└────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘
     │          │          │          │
     ▼          ▼          ▼          ▼
┌─────────────────────────────────────────────────────┐
│                  Data Layer                           │
│                                                      │
│  ┌───────────┐  ┌───────────┐  ┌──────────────────┐ │
│  │  MongoDB  │  │   Redis   │  │  File Storage    │ │
│  │  (Primary │  │  (Cache,  │  │  (Local/S3 for   │ │
│  │   Store)  │  │  Sessions)│  │   images)        │ │
│  └───────────┘  └───────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────┘
```

## 3. Monorepo Structure

```
WF_Main/
├── CLAUDE.md                          # Project truths
├── documents/                         # Planning, specs, design docs
│   └── Planning/                      # This directory
├── WildernessFriends/                 # React Native / Expo Go app
├── services/                          # All backend services
│   ├── docker-compose.yml             # Orchestrates all services + databases
│   ├── docker-compose.dev.yml         # Dev overrides (hot-reload, volumes)
│   ├── .env.example                   # Template for environment variables
│   ├── .dockerignore                  # Excludes node_modules, __pycache__, .env from builds
│   ├── shared/                        # Shared utilities across Python services
│   │   ├── __init__.py                # Package init
│   │   └── python/                    # Import as: from shared.python.<module> import ...
│   │       ├── __init__.py
│   │       ├── auth.py                # JWT verify, API key check, get_current_user dependency
│   │       ├── responses.py           # success_response / error_response (datetime-safe)
│   │       ├── middleware.py          # RequestLoggingMiddleware, global_exception_handler
│   │       └── config.py             # BaseServiceConfig (pydantic-settings)
│   ├── node-gateway/                  # Node.js API Gateway
│   │   ├── Dockerfile
│   │   ├── package.json
│   │   ├── src/
│   │   │   ├── server.js              # Express app entry
│   │   │   ├── middleware/            # Auth, rate-limit, proxy
│   │   │   ├── routes/                # Route definitions
│   │   │   └── config/               # Service URLs, JWT config
│   │   └── tests/                     # Jest tests
│   ├── permissions-service/           # Permissions & entitlements
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── app/
│   │   │   ├── main.py               # FastAPI entry
│   │   │   ├── models/               # Pydantic models
│   │   │   ├── routes/               # API endpoints
│   │   │   ├── services/             # Business logic
│   │   │   └── database.py           # MongoDB connection
│   │   └── tests/                     # pytest tests
│   ├── commerce-service/              # Stripe, cart, orders
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── app/
│   │   └── tests/
│   ├── image-service/                 # Image storage & processing
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── app/
│   │   └── tests/
│   └── llm-service/                   # AI text & image generation
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── app/
│       └── tests/
└── tests/                             # Cross-service integration tests
    ├── conftest.py
    └── integration/
```

## 4. Technology Decisions

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Mobile App | React Native + Expo SDK 52 | Already in place |
| Auth | Firebase Auth | Already in place, proven pattern |
| API Gateway | Node.js / Express | Proven in reference project, good proxy support |
| Backend Services | Python / FastAPI | Async, Pydantic validation, LLM/AI ecosystem |
| Primary Database | MongoDB | Flexible schema, document model fits our data |
| Cache / Sessions | Redis | Fast k/v, cart persistence, rate-limit counters |
| File Storage | Local (Docker volume) + S3-ready | Start local, interface allows cloud migration |
| Containerization | Docker + docker-compose | Consistent environments, hot-reload dev setup |
| Testing (Python) | pytest + httpx (async) | Standard FastAPI testing stack |
| Testing (Node) | Jest + supertest | Standard Express testing stack |
| CI/CD | GitHub Actions (future) | Will define when deploying |

## 5. Shared Patterns (All Services)

### 5.1 Authentication Flow

```
Mobile App
    │
    ├─ Firebase Auth → ID Token
    │
    ▼
API Gateway
    │
    ├─ Verify Firebase ID Token
    ├─ Fetch user permissions from Permissions Service
    ├─ Generate internal JWT (1hr expiry, HS256)
    │   └─ Payload: { uid, email, permissions, role }
    │
    ▼
Backend Service
    │
    ├─ Verify internal JWT (fast, no Firebase call)
    └─ Check permissions from JWT payload
```

### 5.2 Standardized Response Format

All services return:

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
  "error_code": "PERMISSION_DENIED",
  "detail": "User lacks 'premium_features' permission"
}
```

### 5.3 HTTP Status Code Convention

| Code | Usage |
|------|-------|
| 200 | Success |
| 201 | Created |
| 400 | Validation error |
| 401 | Not authenticated |
| 403 | Not authorized (permission denied) |
| 404 | Not found |
| 409 | Conflict (duplicate) |
| 429 | Rate limited |
| 500 | Server error |

### 5.4 Service Health Checks

Every service exposes:
- `GET /health` — simple alive check
- `GET /health/detailed` — checks dependencies (DB, Redis, external APIs)

### 5.5 Environment Configuration

All services load config from environment variables. A `.env.example` file documents every required variable. Docker-compose maps `.env` files per service.

### 5.6 Logging Standard

```
[SERVICE_NAME] [LEVEL] [TIMESTAMP] Message
[GATEWAY] [INFO] 2026-03-01T12:00:00Z POST /api/auth/token 200 45ms
[PERMISSIONS] [ERROR] 2026-03-01T12:00:01Z Failed to fetch user: connection timeout
```

## 6. Docker Development Setup

### 6.1 Hot-Reload Strategy

| Service | Mechanism | How |
|---------|-----------|-----|
| Node Gateway | nodemon | Volume mount `./node-gateway/src` → watches for changes |
| Python Services | uvicorn --reload | Volume mount `./service/app` → auto-restart on save |
| MongoDB | Persistent volume | Data survives container restarts |
| Redis | Persistent volume (optional) | Cache can be ephemeral in dev |

### 6.2 Docker Compose Services

```yaml
# Simplified structure — full config in docker-compose.yml
services:
  mongodb:       # Port 27017
  redis:         # Port 6379
  gateway:       # Port 3000, depends on mongodb, redis
  permissions:   # Port 5003, depends on mongodb
  commerce:      # Port 3004, depends on mongodb, redis
  image-service: # Port 5001, depends on mongodb
  llm-service:   # Port 5000
```

### 6.3 Development Workflow

```bash
# Start all services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Restart a single service after dependency changes
docker-compose restart permissions

# View logs for a specific service
docker-compose logs -f commerce

# Run tests inside a service container
docker-compose exec permissions pytest

# Rebuild after Dockerfile changes
docker-compose build permissions && docker-compose up -d permissions
```

## 7. Service Overview

| Service | Port | Responsibility | Planning Doc |
|---------|------|---------------|--------------|
| Node Gateway | 3000 | Auth, routing, proxy, JWT | 01_NODE_GATEWAY_PLAN.md |
| Permissions | 5003 | Entitlements, subscriptions, feature gating | 02_PERMISSIONS_SERVICE_PLAN.md |
| Commerce | 3004 | Stripe, cart, checkout, orders, subscriptions | 03_COMMERCE_SERVICE_PLAN.md |
| Image | 5001 | Upload, process, store, serve images | 04_IMAGE_SERVICE_PLAN.md |
| LLM | 5000 | Text gen, image gen, provider factory | 05_LLM_SERVICE_PLAN.md |
| Testing | — | Unit + integration test strategy | 06_TESTING_STRATEGY.md |

## 8. Service Dependencies

```
Permissions Service  ← standalone (no service deps)
Commerce Service     ← depends on: Permissions (check entitlements)
Image Service        ← depends on: LLM Service (AI generation)
LLM Service          ← standalone (external provider APIs only)
Node Gateway         ← depends on: ALL services (proxy layer)
```

## 9. Build Order (Recommended)

### Phase 1: Foundation (no app features needed)
1. **Docker infrastructure** — docker-compose, MongoDB, Redis
2. **Shared utilities** — auth, responses, middleware, config
3. **Node Gateway** — Express app, Firebase auth verification, JWT, health
4. **Permissions Service** — CRUD permissions, subscription tiers, feature metering

### Phase 2: Core Services
5. **Commerce Service** — Stripe integration, cart, checkout, orders
6. **Image Service** — Upload, storage, processing, serving
7. **LLM Service** — Provider factory, text generation, image generation

### Phase 3: Integration
8. **Mobile app SDK/hooks** — React Native hooks to call services via gateway
9. **Cross-service integration tests**
10. **Gateway route wiring** — connect all proxy routes

## 10. Security Principles

1. **No secrets in code** — all credentials via environment variables
2. **Firebase token verification** — every request authenticated at gateway
3. **Internal JWT** — services trust gateway-issued JWTs, no re-verification of Firebase
4. **API key for service-to-service** — backend services reject requests without valid API key or JWT
5. **Input validation** — Pydantic models validate all inputs at service boundary
6. **Permission checks** — every gated action checks entitlements before execution
7. **Rate limiting** — applied at gateway level per user/IP
8. **CORS** — restrictive in production, permissive in development only

## 11. Open Questions for Future Planning

- Notification service (push notifications for orders, subscription events)?
- Analytics service (usage tracking, dashboards)?
- Admin panel (web-based management interface)?
- CDN for image delivery in production?
- WebSocket/SSE for real-time features (chat streaming)?

These will be planned as separate services when the need arises, following the same patterns defined here.

## 12. Implementation Notes (Phase 1 — Completed)

Key patterns established during Phase 1 build that future services must follow:

### 12.1 Docker Build Context for Python Services
Python services that import shared utilities cannot use their own directory as the Docker build context (Docker doesn't allow `COPY ../shared`). Instead:
- **docker-compose.yml** sets `context: .` (services root) and `dockerfile: <service>/Dockerfile`
- **Dockerfile** copies relative to services root: `COPY shared/ /app/shared/` and `COPY <service>/app/ /app/app/`
- **PYTHONPATH=/app** in the Dockerfile ensures `from shared.python.auth import ...` resolves

### 12.2 JSON Datetime Serialisation
MongoDB returns `datetime` objects. FastAPI's `JSONResponse` uses stdlib `json.dumps` which can't handle datetime. The shared `responses.py` uses a custom `_DateTimeEncoder` to automatically convert datetime to ISO 8601 strings. All responses must go through `success_response()` / `error_response()`.

### 12.3 Gateway Proxy Path Handling
Express strips the router mount prefix before passing to `http-proxy-middleware`. For example, `app.use('/api', router)` + `router.use('/permissions', proxy)` means the proxy sees `req.url = /{userId}` not `/api/permissions/{userId}`. The fix uses `config.pathPrefix` in the `proxyReq` handler to prepend the backend route prefix (e.g., `/permissions`).

### 12.4 FastAPI Route Ordering
Static routes must be defined before parameterized routes in the same router. e.g., `GET /subscriptions/tiers` must appear before `GET /subscriptions/{user_id}`, otherwise FastAPI matches "tiers" as a user_id.

### 12.5 Windows + Docker File Watching
Nodemon inside Docker may not detect file changes made from the Windows host through volume mounts. After editing gateway source files, restart the container: `docker-compose restart gateway`.

### 12.6 Gateway Dockerfile
Uses `npm install` (not `npm ci`) because no `package-lock.json` is committed. The `.dockerignore` at `node-gateway/` excludes `node_modules` and `tests` from the build context.
