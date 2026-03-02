# API Gateway - Quick Reference

## Overview

The API Gateway is a **Node.js/Express** service running on **port 3000**. It is the single external entry point for the WildernessFriends mobile app. All traffic from the app flows through this gateway before reaching any backend Python service.

Responsibilities:
- **Auth verification** - validates Firebase tokens and internal JWTs
- **Rate limiting** - protects all routes and auth endpoints specifically
- **Proxying** - forwards authenticated requests to the appropriate backend service

---

## Middleware Stack

Middleware is applied in this exact order for every incoming request:

| Order | Middleware | Purpose |
|-------|-----------|---------|
| 1 | `requestLogger` | Logs `[GATEWAY] METHOD PATH STATUS DURATIONms` |
| 2 | `helmet` | Sets secure HTTP response headers |
| 3 | `CORS` | Handles cross-origin requests (configured via `CORS_ORIGINS`) |
| 4 | `globalLimiter` | Rate limits all IPs to 100 requests/minute |
| 5 | body parser (JSON) | Parses JSON request bodies up to 1MB |
| 6 | routes | Auth, health, and proxy route handlers |

---

## Endpoints

| Method/Pattern | Path | Auth Required | Description |
|---------------|------|--------------|-------------|
| `GET` | `/health` | None | Gateway alive check |
| `GET` | `/health/services` | None | Aggregated health of all backend services |
| `POST` | `/api/auth/token` | Firebase token | Exchange Firebase ID token for internal JWT (rate limited: 10 req/min) |
| `GET` | `/api/auth/verify` | Internal JWT | Verify JWT validity |
| `*` | `/api/permissions/**` | Internal JWT | Proxy to Permissions Service (:5003) |
| `*` | `/api/commerce/**` | Internal JWT | Proxy to Commerce Service (:3004) |
| `POST` | `/api/commerce/webhooks/**` | None (Stripe signature) | Proxy to Commerce Service webhooks (auth bypassed) |
| `*` | `/api/images/**` | Internal JWT | Proxy to Image Service (:5001) |
| `*` | `/api/llm/**` | Internal JWT | Proxy to LLM Service (:5000) |
| `*` | `/api/chat/**` | Internal JWT | Proxy to LLM Service (:5000) via `/chat` prefix |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NODE_ENV` | - | Runtime environment (`development`, `production`) |
| `GATEWAY_PORT` | `3000` | Port the gateway listens on |
| `JWT_SECRET` | - | Secret for signing/verifying internal JWTs (HS256) |
| `JWT_EXPIRY` | `1h` | Expiry duration for issued internal JWTs |
| `INTERNAL_API_KEY` | - | API key injected into proxied requests (`X-Api-Key` header) |
| `FIREBASE_PROJECT_ID` | - | Firebase project identifier |
| `FIREBASE_CLIENT_EMAIL` | - | Firebase Admin SDK service account email |
| `FIREBASE_PRIVATE_KEY` | - | Firebase Admin SDK private key |
| `PERMISSIONS_SERVICE_URL` | - | Base URL for Permissions Service (e.g. `http://permissions:5003`) |
| `COMMERCE_SERVICE_URL` | - | Base URL for Commerce Service (e.g. `http://commerce:3004`) |
| `IMAGES_SERVICE_URL` | - | Base URL for Image Service (e.g. `http://images:5001`) |
| `LLM_SERVICE_URL` | - | Base URL for LLM Service (e.g. `http://llm:5000`) |
| `CORS_ORIGINS` | - | Comma-separated list of allowed CORS origins |

---

## Commands

```bash
# Start in production mode
npm start

# Start in development mode with live reload (nodemon)
npm run dev

# Run all tests
npm test

# Run unit tests only
npm run test:unit

# Run integration tests only
npm run test:integration

# Run tests with coverage report
npm run test:coverage

# Run tests in watch mode
npm run test:watch
```

---

## Common Errors

| HTTP Status | `error_code` | Cause | Resolution |
|-------------|-------------|-------|-----------|
| `401` | `AUTH_REQUIRED` | No `Authorization: Bearer <token>` header present | Include a valid Bearer token in the request header |
| `401` | `AUTH_INVALID` | Token is malformed, expired, or fails verification | Re-authenticate to obtain a fresh token |
| `429` | `RATE_LIMITED` | IP has exceeded the allowed request rate | Reduce request frequency; respect rate limit headers |
| `503` | `SERVICE_UNAVAILABLE` | The target backend service is unreachable or down | Check backend service health; retry after recovery |

---

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `express` | HTTP server and routing framework |
| `jsonwebtoken` | HS256 JWT signing and verification |
| `firebase-admin` | Firebase ID token verification |
| `http-proxy-middleware` | Proxies requests to backend services |
| `express-rate-limit` | IP-based rate limiting |
| `helmet` | Secure HTTP headers |
| `cors` | Cross-origin request handling |
| `axios` | HTTP client used for service health checks and permission fetches |
