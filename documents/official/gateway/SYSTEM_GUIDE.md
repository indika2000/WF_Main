# API Gateway - System Guide

## Table of Contents

1. [Auth Flow](#auth-flow)
2. [Permissions Middleware](#permissions-middleware)
3. [Token Exchange Route](#token-exchange-route)
4. [Proxy Architecture](#proxy-architecture)
5. [Rate Limiting](#rate-limiting)
6. [JWT Utils](#jwt-utils)
7. [Response Utils](#response-utils)
8. [Error Handler](#error-handler)
9. [File Structure](#file-structure)

---

## Auth Flow

Authentication is handled by `authMiddleware` (`src/middleware/auth.js`). It uses a two-path strategy: **internal JWT first**, with a fallback to **Firebase token verification**.

### Public Paths (No Auth)

The following paths bypass `authMiddleware` entirely:

```
/health
/health/services
```

### Internal JWT Path (Fast / Common Path)

This is the primary path for all SDK requests after the initial token exchange.

1. Extract the `Authorization: Bearer <token>` header.
2. Attempt to verify the token as an **HS256 JWT** using `jsonwebtoken` and `JWT_SECRET`.
3. If verification succeeds:
   - Set `req.user` with `{ uid, email }`
   - Set `req.internalToken` (the raw token string)
   - Set `req.permissions` and `req.subscription` from the JWT payload
   - **Return immediately** - no further verification needed.

### Firebase Fallback Path

Used when the token fails internal JWT verification (e.g. fresh Firebase login before first token exchange).

1. Internal JWT verification throws.
2. Fall through to Firebase Admin `verifyIdToken(token)`.
3. If Firebase verification succeeds:
   - Set `req.user` with `{ uid, email }` from the decoded Firebase token.
   - `req.internalToken`, `req.permissions`, and `req.subscription` are **not set** at this stage.
4. If Firebase verification also fails: return `401 AUTH_INVALID`.

### Development Bypass

When `NODE_ENV` is **not** `production`, a request carrying `Authorization: Bearer dev-bypass` skips all verification and creates a synthetic `dev-user` identity on `req.user`. This is for local development only and is never active in production.

### Auth Flow Diagram

```
Incoming Request
       |
       v
Is path in PUBLIC_PATHS?
  Yes --> skip auth, call next()
  No  --> extract Bearer token
             |
             v
     Try verifyToken(token) [HS256]
             |
        Success?
       /       \
     Yes        No
      |          |
Set req.user   Try Firebase verifyIdToken(token)
Set req.internalToken      |
Set req.permissions   Success?
Set req.subscription  /      \
call next()         Yes       No
                     |         |
               Set req.user  401 AUTH_INVALID
               call next()
```

---

## Permissions Middleware

`permissionsMiddleware` (`src/middleware/permissions.js`) enriches the request with user permissions and subscription data, then signs a new internal JWT.

### When It Is Skipped

- `req.user` is not set (public routes that bypassed auth)
- `req.internalToken` is already set (the request carried a valid internal JWT; permissions are already embedded in the token payload)

### Execution Steps

1. **Fetch permissions** - `GET /permissions/{uid}` on the Permissions Service with `X-Api-Key` header.
2. **Auto-create user** - If the Permissions Service returns `404`, automatically call `POST /permissions/{uid}` with `{ email }` to create the user record.
3. **Fetch subscription** - `GET /subscriptions/{uid}` on the Permissions Service. If `404`, default to `{ tier: 'free', status: 'active' }`.
4. **Sign new internal JWT** - Call `signToken()` with payload:

```js
{
  uid,
  email,
  role,
  is_premium,
  permissions,
  subscription_tier
}
```

5. **Attach to request** - Set `req.internalToken`, `req.permissions`, and `req.subscription`.
6. Call `next()`.

---

## Token Exchange Route

**`POST /api/auth/token`** (`src/routes/auth.js`)

This route allows the mobile app to exchange a Firebase ID token for a signed internal JWT. It is the entry point for authenticated sessions.

### Rate Limiting

Protected by `authLimiter`: **10 requests per minute per IP**. This is stricter than the global limiter and is applied only to this route.

### Request

```http
POST /api/auth/token
Authorization: Bearer <firebase-id-token>
```

### Processing Steps

1. Extract and verify the Firebase ID token directly (does **not** go through `authMiddleware`).
2. Call `permissionsMiddleware` manually via a Promise wrapper to fetch/create permissions and sign the internal JWT.
3. Return the signed token and enriched user object.

### Response

```json
{
  "success": true,
  "message": "Token issued",
  "data": {
    "token": "<internal-jwt>",
    "user": {
      "uid": "firebase-uid",
      "email": "user@example.com",
      "role": "user",
      "is_premium": false,
      "permissions": ["scan", "collect"],
      "subscription": {
        "tier": "free",
        "status": "active"
      }
    }
  }
}
```

### Token Verification Route

**`GET /api/auth/verify`** - Requires a valid internal JWT. Returns the decoded payload to confirm the token is valid and not expired. Useful for client-side session validation.

---

## Proxy Architecture

All backend proxying is handled in `src/routes/proxy.js` using `http-proxy-middleware`'s `createProxyMiddleware`.

### Service Configuration

`config/services.js` exports a `SERVICE_CONFIG` map. Each entry defines the backend target and optional path transformation:

| Service Key | Port | `pathPrefix` | Notes |
|------------|------|-------------|-------|
| `permissions` | `:5003` | `/permissions` | Prefixed to all forwarded URLs |
| `commerce` | `:3004` | `''` | No prefix; paths forwarded as-is |
| `images` | `:5001` | `/images` | Prefixed to all forwarded URLs |
| `llm` | `:5000` | `''` | No prefix |
| `chat` | `:5000` | `/chat` | Same host as LLM, `/chat` prefix applied |

```js
// Example SERVICE_CONFIG shape
const SERVICE_CONFIG = {
  permissions: {
    url: process.env.PERMISSIONS_SERVICE_URL,
    timeout: 5000,
    pathPrefix: '/permissions'
  },
  commerce: {
    url: process.env.COMMERCE_SERVICE_URL,
    timeout: 10000,
    pathPrefix: ''
  },
  // ...
};
```

### ProxyReq Handler

For every proxied request, a `onProxyReq` handler runs before the request is forwarded. It:

1. **Injects `Authorization` header** - `Bearer <req.internalToken>` so the backend service can trust the caller.
2. **Injects `X-Api-Key` header** - The value of `INTERNAL_API_KEY`, used by backend services to verify the request originated from the gateway.
3. **Injects `X-User-ID` header** - `req.user.uid`, allowing backend services to identify the user without decoding a token.
4. **Calls `fixRequestBody`** - Re-attaches the parsed JSON body (required when `bodyParser` has already consumed the raw stream before `http-proxy-middleware` forwards it).
5. **Prepends `pathPrefix`** - Rewrites the request URL to include the service's `pathPrefix` before forwarding.

### Webhook Bypass

Commerce webhook routes (`/api/commerce/webhooks/**`) require the raw, unparsed request body so Stripe can validate its HMAC signature. These routes:

1. Check if `req.path` starts with `/webhooks`.
2. If yes: call `next('route')` to skip the authenticated proxy middleware.
3. A separate, unauthenticated proxy middleware handles these requests without injecting auth headers or re-attaching the parsed body.

---

## Rate Limiting

All rate limiters use `express-rate-limit` with `standardHeaders: true` and `legacyHeaders: false`.

| Limiter | Limit | Window | Mounted On |
|---------|-------|--------|-----------|
| `globalLimiter` | 100 requests | 1 minute per IP | All routes (in `app.js` middleware stack) |
| `authLimiter` | 10 requests | 1 minute per IP | `POST /api/auth/token` only |
| `aiLimiter` | 5 requests | 1 minute per IP | Defined in `rateLimiter.js` - **not yet mounted** |

```js
// rateLimiter.js - example shape
const globalLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
});

const authLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 10,
  standardHeaders: true,
  legacyHeaders: false,
});

const aiLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 5,
  standardHeaders: true,
  legacyHeaders: false,
});
```

When a limiter triggers, the response is:

```json
{
  "success": false,
  "message": "Too many requests",
  "error_code": "RATE_LIMITED"
}
```

---

## JWT Utils

**`src/utils/jwt.js`**

### `signToken(payload, expiresIn?)`

Signs a new HS256 JWT.

```js
signToken(payload, expiresIn)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `payload` | `object` | required | Data to encode in the token |
| `expiresIn` | `string` | `process.env.JWT_EXPIRY` or `'1h'` | Token expiry (e.g. `'1h'`, `'7d'`) |

Returns a signed JWT string.

### `verifyToken(token)`

Verifies a JWT and returns its decoded payload.

```js
verifyToken(token)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `token` | `string` | The JWT string to verify |

Returns the decoded payload object. Throws a `JsonWebTokenError` or `TokenExpiredError` if verification fails.

### Example Usage

```js
const { signToken, verifyToken } = require('./utils/jwt');

// Sign
const token = signToken({ uid: 'abc123', email: 'user@example.com' });

// Verify
try {
  const payload = verifyToken(token);
  console.log(payload.uid); // 'abc123'
} catch (err) {
  // Handle invalid or expired token
}
```

---

## Response Utils

**`src/utils/responses.js`**

Provides consistent JSON response shapes across all routes.

### `successResponse(res, data, message, statusCode?)`

```js
successResponse(res, data, message, statusCode = 200)
```

Sends a successful response:

```json
{
  "success": true,
  "message": "Operation completed",
  "data": { }
}
```

### `errorResponse(res, message, errorCode, statusCode, detail?)`

```js
errorResponse(res, message, errorCode, statusCode, detail)
```

Sends an error response:

```json
{
  "success": false,
  "message": "Something went wrong",
  "error_code": "AUTH_INVALID",
  "detail": "Token has expired"
}
```

The `detail` field is optional and omitted when not provided.

### Standard Error Codes

| `error_code` | HTTP Status | Usage |
|-------------|-------------|-------|
| `AUTH_REQUIRED` | `401` | No Authorization header present |
| `AUTH_INVALID` | `401` | Token verification failed |
| `RATE_LIMITED` | `429` | Rate limiter triggered |
| `SERVICE_UNAVAILABLE` | `503` | Backend service unreachable |
| `INTERNAL_ERROR` | `500` | Unhandled server error |

---

## Error Handler

**`src/middleware/errorHandler.js`**

A global Express error handler registered as a **4-argument middleware** and mounted **last** in `app.js` after all routes.

```js
// Must be 4 args for Express to treat it as an error handler
app.use((err, req, res, next) => { ... });
```

### Behavior

- Catches any error passed via `next(err)` from routes or middleware.
- Always returns HTTP `500` with a consistent error body:

```json
{
  "success": false,
  "message": "An unexpected error occurred",
  "error_code": "INTERNAL_ERROR"
}
```

- **In production (`NODE_ENV=production`)**: Stack traces are suppressed from the response.
- **In development**: Stack traces may be included in server logs for debugging, but are not sent to the client.

---

## File Structure

```
node-gateway/
├── Dockerfile
├── package.json
├── .dockerignore
├── src/
│   ├── server.js               # Entry point: creates HTTP server, listens on GATEWAY_PORT
│   ├── app.js                  # Express app: middleware stack + route mounting
│   ├── config/
│   │   ├── firebase.js         # Firebase Admin SDK init (idempotent - safe to import multiple times)
│   │   └── services.js         # SERVICE_CONFIG map (service name -> url, timeout, pathPrefix)
│   ├── middleware/
│   │   ├── auth.js             # authMiddleware: JWT verification + Firebase fallback
│   │   ├── permissions.js      # permissionsMiddleware: fetch permissions + sign internal JWT
│   │   ├── rateLimiter.js      # globalLimiter, authLimiter, aiLimiter
│   │   ├── requestLogger.js    # Logs [GATEWAY] METHOD PATH STATUS DURATIONms
│   │   └── errorHandler.js     # Global 500 error handler (4-arg Express middleware)
│   ├── routes/
│   │   ├── auth.js             # POST /token, GET /verify
│   │   ├── health.js           # GET / (gateway check), GET /services (aggregate health)
│   │   └── proxy.js            # All proxy routes to backend services
│   └── utils/
│       ├── jwt.js              # signToken(payload, expiresIn), verifyToken(token)
│       └── responses.js        # successResponse(...), errorResponse(...)
└── tests/
    ├── jest.config.js
    ├── helpers/
    │   ├── mockFirebase.js     # Firebase Admin mock for tests
    │   └── mockServices.js     # Mock backend service responses
    ├── unit/
    │   ├── jwt.test.js         # signToken / verifyToken unit tests
    │   └── responses.test.js   # Response shape unit tests
    └── integration/
        ├── auth.test.js        # Token exchange + verify endpoint tests
        ├── health.test.js      # Health endpoint tests
        └── rateLimiter.test.js # Rate limiting behavior tests
```

### Module Responsibilities Summary

| File | Responsibility |
|------|---------------|
| `server.js` | Creates the raw Node.js HTTP server and binds to `GATEWAY_PORT` |
| `app.js` | Assembles the Express app: applies middleware in order, mounts all routers |
| `config/firebase.js` | Initializes Firebase Admin SDK once using environment variables |
| `config/services.js` | Central registry of all backend service URLs and routing config |
| `middleware/auth.js` | Authenticates requests via internal JWT or Firebase fallback |
| `middleware/permissions.js` | Enriches request with permissions/subscription; signs new JWT if needed |
| `middleware/rateLimiter.js` | Exports all rate limiter instances |
| `middleware/requestLogger.js` | Logs each request with method, path, status, and duration |
| `middleware/errorHandler.js` | Catches unhandled errors; returns sanitized 500 responses |
| `routes/auth.js` | Handles token exchange and verification endpoints |
| `routes/health.js` | Returns gateway liveness and aggregated backend health |
| `routes/proxy.js` | Configures and mounts all `http-proxy-middleware` instances |
| `utils/jwt.js` | Pure JWT sign/verify helpers |
| `utils/responses.js` | Standardized success/error JSON response helpers |
