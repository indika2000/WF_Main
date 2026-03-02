# Permissions Service - Quick Reference

## Overview

FastAPI permissions and entitlements service running on **port 5003** with **MongoDB** as the data store. Manages user roles, feature permissions, subscription tiers, and usage metering for all downstream services.

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/health` | None | Service alive check |
| `GET` | `/health/detailed` | None | Checks MongoDB connectivity |
| `POST` | `/permissions/{user_id}` | API Key / JWT | Create default permissions for new user |
| `GET` | `/permissions/{user_id}` | API Key / JWT | Get user permissions |
| `PATCH` | `/permissions/{user_id}` | API Key / JWT | Update permissions (partial) |
| `GET` | `/permissions/{user_id}/check/{permission}` | API Key / JWT | Check single permission |
| `GET` | `/subscriptions/tiers` | API Key / JWT | List all tier definitions |
| `POST` | `/subscriptions/{user_id}` | API Key / JWT | Create / upsert subscription |
| `GET` | `/subscriptions/{user_id}` | API Key / JWT | Get subscription |
| `POST` | `/subscriptions/{user_id}/sync` | API Key / JWT | Force sync permissions to tier |
| `GET` | `/usage/{user_id}/{feature}` | API Key / JWT | Get usage record |
| `POST` | `/usage/{user_id}/{feature}/check` | API Key / JWT | Check if usage is allowed |
| `POST` | `/usage/{user_id}/{feature}/record` | API Key / JWT | Increment usage by 1 |
| `POST` | `/usage/{user_id}/{feature}/bonus` | API Key / JWT | Add bonus uses |
| `POST` | `/usage/reset-expired` | API Key / JWT | Reset all expired usage periods |
| `GET` | `/admin/users` | Admin JWT | List users (paginated) |
| `PATCH` | `/admin/users/{user_id}/role` | Admin JWT | Change user role |

---

## Subscription Tiers

| Tier | Price | Key Permissions | AI Text Limit | AI Image Limit |
|------|-------|-----------------|---------------|----------------|
| `free` | $0 | `ai_text_generation` only | 10 / month | 0 |
| `premium` | $4.99 | + `ad_free`, `premium_features`, `ai_image_generation`, `advanced_search` | 100 / month | 25 / month |
| `ultra` | $9.99 | + `unlimited_storage`, `priority_support` | Unlimited | Unlimited |

---

## Permission Flags

All permission flags are booleans, defaulting to `false` on user creation:

| Flag | Description |
|------|-------------|
| `ad_free` | User does not see advertisements |
| `premium_features` | Access to premium UI features |
| `ai_text_generation` | May use AI text generation |
| `ai_image_generation` | May use AI image generation |
| `advanced_search` | Access to advanced search filters |
| `unlimited_storage` | No storage cap enforced |
| `priority_support` | Routed to priority support queue |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `MONGODB_URI` | MongoDB connection string |
| `INTERNAL_API_KEY` | Shared secret for service-to-service calls |
| `JWT_SECRET` | Secret for verifying JWT tokens |
| `SERVICE_NAME` | Identifier used in logs and health responses |

---

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Unit tests only
pytest tests/unit -v

# Integration tests only
pytest tests/integration -v
```

---

## Common Errors

| Code | Error | Meaning |
|------|-------|---------|
| `404` | `USER_NOT_FOUND` | No permissions record exists for the given user_id |
| `409` | `USER_EXISTS` | Attempted to create permissions for a user_id that already exists |
| `400` | `INVALID_TIER` | Subscription tier value is not one of: free, premium, ultra |
