# WildernessFriends — Lessons Learned & Gotchas

This document captures every significant issue, workaround, and pattern discovered during the 4-phase build. Each item is something that failed or caused confusion initially and was fixed — documented here so future development avoids the same pitfalls.

---

## Docker & Infrastructure

### 1. Python Services Must Use Services Root as Docker Build Context

Docker cannot `COPY ../shared` — it rejects paths outside the build context. All Python services set `context: .` (the `services/` root) in docker-compose.yml and use `dockerfile: <service>/Dockerfile`. Inside each Dockerfile:
```dockerfile
COPY shared/ /app/shared/
COPY permissions-service/app/ /app/app/
COPY permissions-service/requirements.txt /app/requirements.txt
ENV PYTHONPATH=/app
```
The gateway is the exception — it uses `context: ./node-gateway` since it has no shared Python dependencies.

### 2. Gateway Dockerfile Uses `npm install`, Not `npm ci`

No `package-lock.json` is committed to the repository. `npm ci` requires a lockfile and will fail. Use `npm install` in the Dockerfile. If you start committing lockfiles, switch to `npm ci` for deterministic installs.

### 3. `docker-compose restart` Does Not Reload `.env`

`docker-compose restart <service>` keeps the existing container and its environment variables. Changes to `.env` are NOT picked up. You must recreate the container:
```bash
docker-compose up -d <service>    # Recreates with new env vars
docker-compose restart <service>  # Only restarts process, keeps old env
```

### 4. `docker-compose down -v` Destroys ALL Data

The `-v` flag removes named volumes including `mongodb_data`, `redis_data`, and `image_storage`. In development, this means all user accounts, orders, uploaded images, and cart data are permanently destroyed. CI intentionally uses `down -v` for clean state, but never do this in a development environment with data you want to keep.

### 5. Image Storage Requires a Named Volume

The `image_storage` volume persists uploaded and generated images at `/storage` inside the image-service container. Without a named volume, all images are lost on container restart. The volume is defined in `docker-compose.yml` — ensure it's not accidentally removed.

---

## Gateway & Proxy

### 6. Express Strips Router Mount Prefix Before Proxy Sees It

When Express routes are mounted as `app.use('/api', router)` and the router has `router.use('/permissions', proxy)`, the proxy middleware receives `req.url = /{userId}` — NOT `/api/permissions/{userId}`. The path prefix is consumed by Express routing.

**Fix:** Each service in `SERVICE_CONFIG` has a `pathPrefix` field. In the `proxyReq` handler, this prefix is prepended to the request URL before forwarding:
```javascript
proxyReq.path = config.pathPrefix + proxyReq.path;
```
Services with no common prefix (Commerce, LLM) use `pathPrefix: ''`.

### 7. `express.json()` Consumes the Body Before Proxy Can Forward It

Express's JSON body parser reads and consumes the request stream. When `http-proxy-middleware` tries to forward the request, the body is gone. Backend services see an empty body, causing `ClientDisconnect` errors and 30-second timeouts.

**Fix:** Import `fixRequestBody` from `http-proxy-middleware` and call it in every proxy's `proxyReq` handler:
```javascript
const { fixRequestBody } = require('http-proxy-middleware');
// In proxy config:
onProxyReq: (proxyReq, req, res) => {
  fixRequestBody(proxyReq, req, res);
  // ... other header injection
}
```

### 8. Stripe Webhooks Bypass Auth via `next('route')`

Stripe webhook calls carry no JWT — they use signature verification instead. The gateway handles this with Express's `next('route')` pattern:
```javascript
// Authenticated commerce route
router.use('/commerce', (req, res, next) => {
  if (req.path.startsWith('/webhooks')) return next('route');
  authMiddleware(req, res, next);
}, permissionsMiddleware, createServiceProxy(...));

// Unauthenticated fallback — only webhooks reach here
router.use('/commerce', createServiceProxy(...));
```
**Route ordering is critical** — the authenticated route must appear BEFORE the unauthenticated fallback.

### 9. CORS Must Include LAN IP for Physical Device Testing

CORS is configured for `localhost:8081` (Expo Metro) and `localhost:19006` (Expo web) by default. Physical devices on the same LAN connect via the host machine's IP address (e.g., `192.168.x.x:3000`), not `localhost`. Add the host IP to `CORS_ORIGINS` when testing on physical devices.

---

## Python Services

### 10. MongoDB `datetime` Objects Break JSON Serialization

MongoDB returns Python `datetime` objects. FastAPI's `JSONResponse` uses `json.dumps()`, which throws `TypeError: Object of type datetime is not JSON serializable`.

**Fix:** All responses go through `success_response()` / `error_response()` from `shared.python.responses`, which uses a custom `_DateTimeEncoder` that converts datetime to ISO 8601 strings. Never pass raw dicts with datetime values directly to `JSONResponse`.

### 11. FastAPI Static Routes Must Come Before Parameterized Routes

In the same router, `GET /subscriptions/tiers` must be defined BEFORE `GET /subscriptions/{user_id}`. Otherwise FastAPI matches the literal string `"tiers"` as a `user_id` parameter and routes incorrectly.

### 12. `google-genai` SDK Requires Keyword Arguments for `Part.from_text()`

```python
# WRONG — raises TypeError
types.Part.from_text("your text")

# CORRECT
types.Part.from_text(text="your text")
```

### 13. Gemini Model `gemini-2.0-flash` Was Deprecated

Google retired `gemini-2.0-flash` — it returns `404 NOT_FOUND`. The current model is `gemini-2.5-flash`. When upgrading providers, verify model availability. Three files must stay in sync: `gemini_provider.py`, `factory.py`, and `config/providers.yml`.

---

## Commerce & Stripe

### 14. Webhook Route Must Read Raw Body Bytes

Stripe's signature verification requires the exact raw request body. The webhook route reads it with `await request.body()` and passes the bytes directly to `stripe.Webhook.construct_event()`.

**Never declare a Pydantic body model on the webhook route** — Pydantic would parse the JSON and discard the raw bytes, breaking signature verification.

### 15. Stripe SDK Is Synchronous Inside Async FastAPI

`stripe-python` makes synchronous HTTP calls. In FastAPI's async context, this works fine for low traffic because the calls are quick. If blocking becomes a performance issue at scale, wrap Stripe calls in `asyncio.to_thread()`.

### 16. Server-Side Price Recalculation — Never Trust the Client

Cart totals are always recomputed server-side by `_recalculate_totals()`. Client-provided totals are ignored:
```python
subtotal = sum(item.unit_price * item.quantity for item in cart.items)
tax = 0        # Digital goods
shipping = 0   # Digital delivery
total = subtotal
```
This is a security requirement — never trust item prices from the client.

### 17. Commerce → Permissions Sync on Subscription Events

When Stripe fires subscription webhooks (`customer.subscription.created/updated/deleted`), the Commerce Service calls the Permissions Service via HTTP:
```python
await httpx.post(f"{PERMISSIONS_URL}/subscriptions/{user_id}", json={...}, headers={"X-Api-Key": api_key})
```
Commerce does not update permissions directly — it notifies the Permissions Service, which owns the permission state and applies tier-specific permission flags.

### 18. Stripe Test Keys and Price IDs Must Be Created Manually

`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_PREMIUM`, and `STRIPE_PRICE_ULTRA` are placeholders in `.env.example`. Before testing subscription flows:
1. Create a Stripe test account
2. Create Products with Price IDs in the Stripe Dashboard (test mode)
3. Set real test keys in `services/.env`
4. Recreate the commerce container: `docker-compose up -d commerce`

### 19. `stripe listen` Webhook Secret Is Session-Scoped

Running `stripe listen --forward-to localhost:3004/webhooks/stripe` generates a temporary signing secret (`whsec_xxxxx`). This secret is specific to the CLI session — a new session generates a new secret. Update `STRIPE_WEBHOOK_SECRET` in `.env` each time and recreate the commerce container.

### 20. MongoDB Sparse Unique Index with `null` Values

MongoDB sparse indexes skip documents **missing** a field, but NOT documents with explicit `null`. When inserting a subscription record with `stripe_subscription_id: null`, the sparse unique index sees it as a real value and throws `DuplicateKeyError` on the second insert.

**Fix:** Use `model_dump(exclude_none=True)` when inserting to MongoDB, so `None` fields are omitted entirely rather than stored as `null`:
```python
doc = sub.model_dump(exclude_none=True)
await db.subscriptions.insert_one(doc)
```

---

## Testing

### 21. Environment Variables Must Be Set Before App Import

All Python test conftests set `os.environ` at the very top, before any imports that load the app:
```python
import os
os.environ["MONGODB_URI"] = "mongodb://localhost:27017/test_db"
os.environ["INTERNAL_API_KEY"] = "test-api-key"
# ... all required vars ...

# ONLY THEN import the app
from app.main import app
```
Pydantic-settings reads env vars at class definition time. If the app is imported first, config validation fails.

### 22. FakeRedis Requires Per-Test `FakeServer` for Isolation

FakeRedis instances share state by default. Data from one test leaks into the next, causing phantom items in carts and incorrect test results.

**Fix:** Create a unique `FakeServer` per test:
```python
@pytest.fixture
async def test_redis():
    server = fakeredis.FakeServer()
    r = fakeredis.aioredis.FakeRedis(decode_responses=True, server=server)
    yield r
    await r.close()
```

### 23. SSE `AppStatus` Event Loop Binding in Tests

`sse-starlette` creates a module-level `asyncio.Event` that binds to the first event loop. In tests, each test function may get a new event loop, causing `RuntimeError: Event is bound to a different event loop`.

**Fix:** Autouse fixture to reset the event before each test:
```python
@pytest.fixture(autouse=True)
def reset_sse_app_status():
    try:
        from sse_starlette.sse import AppStatus
        AppStatus.should_exit_event = asyncio.Event()
    except (ImportError, AttributeError):
        pass
```
Required in any service using SSE streaming (currently LLM service).

### 24. Stripe Mocks via `autouse` Monkeypatch Fixture

Commerce tests patch all Stripe SDK calls with a `mock_stripe` fixture marked `autouse=True`. A `MockObj` class simulates Stripe's attribute-based object interface. This ensures no real Stripe API calls happen during tests, even accidentally.

### 25. LLM Provider Factory Injection for Tests

Tests inject mock providers directly into the singleton:
```python
provider_factory._text_providers = {"mock-text": MockTextProvider()}
provider_factory._image_providers = {"mock-image": MockImageProvider()}
```
`LLM_CONFIG_PATH` is set to `/nonexistent/providers.yml` to prevent loading real provider configs.

### 26. Image Service Mock Storage for Tests

Tests inject a `MockStorage` (in-memory dict) via `app.state.storage`, replacing the filesystem-based `LocalStorage`. This avoids filesystem side effects during testing.

### 27. CI Uses `.env.example` — All External API Calls Must Be Mocked

The GitHub Actions workflow copies `.env.example` to `.env` before starting services. All Stripe, AI provider, and Firebase API calls must be mocked in tests — the CI environment has no real API keys.

### 28. CI Must Wait for MongoDB Health Before Running Tests

The CI workflow polls MongoDB health for up to 60 seconds before running tests. Without this wait, services fail to connect and tests produce confusing connection errors.

### 29. Timezone-Aware Datetime Comparison in Tests

`datetime.now(timezone.utc)` returns timezone-aware datetimes, but `mongomock` may return naive datetimes from stored documents. Comparing the two raises `TypeError: can't compare offset-naive and offset-aware datetimes`.

**Fix:** Normalize before comparing:
```python
if period_end and period_end.tzinfo is None:
    period_end = period_end.replace(tzinfo=timezone.utc)
```

### 30. `AsyncMock` vs `MagicMock` for httpx Response Objects

When mocking `httpx` responses, use `MagicMock` (not `AsyncMock`) because `response.json()` is a synchronous method. `AsyncMock` makes `.json()` return a coroutine, causing `'coroutine' object has no attribute 'get'`.

### 31. Health Check Test: Nock `.times(2)` for Shared Service URLs

The LLM and Chat services share the same URL (`http://llm-service:5000`). Health check tests that mock all services need `.times(2)` on the shared URL mock — nock interceptors are consumed once by default.

---

## Mobile SDK

### 32. Axios Auto-Unwraps the Response Envelope

The response interceptor in `api.ts` extracts `response.data.data` automatically. SDK functions return the inner data directly:
```typescript
// In cart.ts:
export async function getCart(userId: string) {
  return api.get(`/commerce/cart/${userId}`);
  // Returns Cart object directly, NOT { success, data: Cart, message }
}
```
When writing new SDK functions, never access `.data.data`.

### 33. `apiReady` Guard Before Making SDK Calls

The mobile app must complete the Firebase → Gateway JWT exchange before any API calls. `AuthContext.apiReady` becomes `true` only after the exchange succeeds. Components and the dev tools screen check `apiReady` before calling SDK functions.

### 34. `localhost` Does Not Work on Android Devices

On Android emulators and physical devices, `localhost` refers to the device itself, not the host machine. The `.env` must use the host machine's LAN IP:
```
EXPO_PUBLIC_API_URL=http://192.168.x.x:3000/api
```
For Android emulator specifically, `10.0.2.2` maps to the host machine's localhost.

### 35. NativeWind Must Be Pinned to `~4.1.23`

NativeWind 4.2+ pulls `react-native-css-interop` 0.2.2, which targets Reanimated v4 and the new `react-native-worklets` package (replacing `react-native-worklets-core`). Since we use Reanimated 3.16, this causes a `__reanimatedLoggerConfig` crash. Pin with tilde (`~`) to prevent minor version bumps.

---

## Development Workflow

### 36. Nodemon Does Not Detect File Changes on Windows + Docker

Nodemon inside Docker containers may not detect file changes made on Windows hosts through volume mounts. After editing gateway source files, manually restart:
```bash
docker-compose restart gateway
```
Python services with `uvicorn --reload` use a polling mechanism that works through volume mounts.

### 37. Dev Bypass Token for Local Testing

In non-production environments, `Authorization: Bearer dev-bypass` is accepted as valid auth, creating a `dev-user` identity. Useful for curl testing. **Must never reach production** — it's gated on `NODE_ENV !== 'production'`.

### 38. Dev Webhook Simulator Bypasses Stripe Signature

`POST /commerce/dev/simulate-webhook` calls the webhook handler directly without signature verification. Only available when `settings.debug` is true. **Must never be enabled in production.**

### 39. Firebase Private Key Format in `.env`

The Firebase private key in `.env` requires escaped newlines as literal `\n` characters:
```
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nMIIE...\n-----END PRIVATE KEY-----"
```
The gateway's `firebase.js` config file handles the `\n` → newline conversion.

---

## Quick Severity Reference

| Severity | Items |
|----------|-------|
| **Breaks build/startup** | #1, #2, #3, #21, #39 |
| **Silent data loss/corruption** | #4, #7, #16, #20 |
| **Silent misrouting** | #6, #8, #11 |
| **Runtime crashes** | #10, #12, #13, #29, #30, #35 |
| **Test failures** | #22, #23, #24, #25, #26, #27, #28, #31 |
| **Dev workflow friction** | #9, #19, #34, #36 |
| **Security considerations** | #14, #37, #38 |
