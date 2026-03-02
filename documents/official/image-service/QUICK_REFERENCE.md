# Image Service - Quick Reference

## Overview

FastAPI-based image service running on **port 5001**. Handles image upload, processing (Pillow-based variant generation), storage, and retrieval. Storage backend uses **MongoDB** for metadata and a **local filesystem** (Docker volume) for binary files. Also proxies AI image generation requests through the **LLM Service**.

---

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | None | Service alive check |
| `GET` | `/health/detailed` | None | Check MongoDB + storage health + disk usage |
| `POST` | `/images/upload` | API Key / JWT | Upload image (multipart/form-data, max 10MB) |
| `GET` | `/images/{image_id}` | API Key / JWT | Get image metadata |
| `GET` | `/images/{image_id}/file` | API Key / JWT | Serve original image binary |
| `GET` | `/images/{image_id}/file/{variant}` | API Key / JWT | Serve variant (thumb/medium/large) as WebP |
| `DELETE` | `/images/{image_id}` | API Key / JWT | Delete image + all variants (owner only) |
| `PATCH` | `/images/{image_id}` | API Key / JWT | Update category / metadata / tags |
| `GET` | `/images/user/{user_id}` | API Key / JWT | List user's images (paginated) |
| `GET` | `/images/user/{user_id}/{category}` | API Key / JWT | List by category (paginated) |
| `POST` | `/images/generate` | API Key / JWT | Generate AI image via LLM Service proxy |

---

## Supported Formats

| Direction | Formats |
|-----------|---------|
| Upload (input) | JPEG, PNG, WebP, GIF |
| Variants (output) | WebP |

---

## Processing Presets

| Preset | Thumb | Medium | Large |
|--------|-------|--------|-------|
| `general` | 150x150 | 400x400 | 800x800 |
| `profile` | 64x64 | 256x256 | 512x512 |
| `card` | 100x140 | 250x350 | 500x700 |

Variants are always output as **WebP** at quality 80. No upscaling: images smaller than the target size are stored at their original dimensions.

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGODB_URI` | MongoDB connection string | Required |
| `INTERNAL_API_KEY` | Shared secret for service-to-service auth | Required |
| `JWT_SECRET` | Secret for verifying JWT tokens | Required |
| `IMAGE_STORAGE_PATH` | Root path for local file storage | `/storage` |
| `IMAGE_MAX_FILE_SIZE` | Maximum upload size in bytes | `10485760` (10MB) |
| `LLM_SERVICE_URL` | Base URL of the LLM Service | Required |

---

## Common Errors

| Code | Error Key | Cause |
|------|-----------|-------|
| `400` | `INVALID_IMAGE_TYPE` | Uploaded file is not JPEG, PNG, WebP, or GIF |
| `400` | `FILE_TOO_LARGE` | File exceeds the 10MB size limit |
| `404` | `IMAGE_NOT_FOUND` | No image record found for the given `image_id` |
| `401` | `UNAUTHORIZED` | Missing or invalid API key / JWT token |
