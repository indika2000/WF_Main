# Image Service - System Guide

## Overview

The Image Service is a FastAPI microservice responsible for the full lifecycle of image assets: upload validation, variant generation, binary storage, metadata persistence, and AI image generation (proxied through the LLM Service). It runs on port 5001 and is called by the API Gateway via `/api/images/*`.

---

## Data Models

### ImageRecord

Persisted to the MongoDB collection `images`.

| Field | Type | Description |
|-------|------|-------------|
| `_id` / `id` | `uuid4` string | Primary identifier |
| `user_id` | string | Owning user's ID |
| `category` | string | Logical category (e.g. `profile`, `card`, `general`) |
| `filename` | string | Original uploaded filename |
| `content_type` | string | MIME type of the original file |
| `file_size` | int | Size of original file in bytes |
| `width` | int | Width of the original image in pixels |
| `height` | int | Height of the original image in pixels |
| `storage_path` | string | Relative path to the original file on disk |
| `variants` | dict | Map of variant name to `ImageVariant` object |
| `source` | string | Either `upload` or `ai_generated` |
| `metadata` | dict | Arbitrary key/value metadata (e.g. AI prompt, model) |
| `tags` | list | List of string tags |
| `created_at` | datetime | Record creation timestamp |
| `updated_at` | datetime | Last modification timestamp |

### ImageVariant

Embedded within `ImageRecord.variants` keyed by variant name (`thumb`, `medium`, `large`).

| Field | Type | Description |
|-------|------|-------------|
| `width` | int | Variant width in pixels |
| `height` | int | Variant height in pixels |
| `storage_path` | string | Relative path to the variant WebP file |
| `file_size` | int | Size of the variant file in bytes |

### GenerateRequest

Request body for `POST /images/generate`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `prompt` | string | Required | Text prompt for AI image generation |
| `category` | string | `"ai_generated"` | Category to assign to generated images |
| `provider` | string | None | Optional provider override (e.g. `openai`) |
| `size` | string | `"1024x1024"` | Output resolution |
| `quality` | string | `"standard"` | Quality tier (provider-specific) |
| `n` | int | `1` | Number of images to generate |
| `tags` | list | `[]` | Tags to apply to generated records |
| `metadata` | dict | `{}` | Additional metadata to store |

---

## Storage Backend Architecture

The storage layer is implemented via a **protocol class** (`StorageBackend`) that defines a common interface. The current implementation uses the local filesystem, but the protocol design allows future migration to object storage (e.g. S3) by implementing the same five methods.

### StorageBackend Protocol

```python
class StorageBackend(Protocol):
    async def save(self, path: str, data: bytes) -> None: ...
    async def load(self, path: str) -> bytes: ...
    async def delete(self, path: str) -> None: ...
    async def exists(self, path: str) -> bool: ...
    async def get_url(self, path: str) -> str: ...
```

### LocalStorage Implementation

- Uses `aiofiles` for non-blocking async I/O on all file operations.
- Base storage root is configurable via `IMAGE_STORAGE_PATH` (defaults to `/storage`).
- File layout on disk:

```
{base_path}/
  {user_id}/
    {image_id}/
      original.{ext}         # Original uploaded file
      thumb.webp             # Thumbnail variant
      medium.webp            # Medium variant
      large.webp             # Large variant
```

- Relative paths stored in MongoDB follow the same structure without the base prefix:
  - Original: `{user_id}/{image_id}/original.{ext}`
  - Variant: `{user_id}/{image_id}/{variant_name}.webp`

### Docker Volume

The local storage directory is mounted via the Docker volume `image_storage` at `/storage` inside the container. This volume must be declared in `docker-compose.yml` and persisted across container restarts.

### Migrating to S3

To migrate storage, implement a new class satisfying the `StorageBackend` protocol with the same five methods (`save`, `load`, `delete`, `exists`, `get_url`) backed by `boto3` or `aiobotocore`. Swap the instance injected at startup in `main.py`. No route or service code changes are required.

---

## Image Processing Pipeline

All processing is handled in `app/processing/image_processor.py` using the **Pillow** library.

### validate_image_file(data: bytes, content_type: str) -> None

1. Checks `content_type` against the whitelist: `image/jpeg`, `image/png`, `image/webp`, `image/gif`.
2. Opens the bytes buffer with Pillow and calls `img.verify()` to confirm the file is a valid image.
3. Raises a `400` error if either check fails.

### get_image_dimensions(data: bytes) -> tuple[int, int]

Opens the bytes buffer with Pillow and returns `(width, height)` of the original image.

### process_image(data: bytes, preset_name: str, output_format: str = "WEBP") -> dict[str, bytes]

Generates all variants defined in the named preset:

1. Looks up the preset dimensions from `PROCESSING_PRESETS` in `app/models/images.py`.
2. For each variant size:
   - Converts RGBA images to RGB when the output format is JPEG (WebP supports alpha).
   - Uses `Image.LANCZOS` resampling for downscaling.
   - **No upscaling**: if the original image is smaller than the target dimensions, the image is stored at its original size without enlargement.
3. Output quality settings:
   - WebP: `quality=80`
   - JPEG: `quality=85`
4. Returns a dict mapping variant name to the processed image bytes.

---

## Upload Flow

`POST /images/upload` (multipart/form-data)

1. Validate `content_type` is in the allowed set (jpeg, png, webp, gif). Return `400 INVALID_IMAGE_TYPE` if not.
2. Validate file size is within the configured limit (<= 10MB). Return `400 FILE_TOO_LARGE` if not.
3. Read all file bytes into memory.
4. Call `validate_image_file(data, content_type)` — Pillow verify confirms the bytes are a valid image.
5. Call `get_image_dimensions(data)` to record original `width` and `height`.
6. Generate a new `uuid4` as `image_id`.
7. Save original bytes to storage at path `{user_id}/{image_id}/original.{ext}`.
8. Determine the processing preset from the request `category` field (falls back to `general`).
9. Call `process_image(data, preset_name)` to generate all variants as WebP bytes.
10. Save each variant to storage at `{user_id}/{image_id}/{variant_name}.webp`.
11. Insert an `ImageRecord` document to MongoDB with full variant metadata and file sizes.
12. Return `201 Created` with the full serialized `ImageRecord`.

---

## AI Generation Proxy

`POST /images/generate` is handled by `app/services/generation_proxy.py`.

### Request to LLM Service

The service calls `POST {LLM_SERVICE_URL}/generate/image` using `httpx.AsyncClient` with:

- **Timeout:** 120 seconds (generation can be slow)
- **Headers:** `X-Api-Key: {INTERNAL_API_KEY}`
- **Body:**

```json
{
  "prompt": "<user prompt>",
  "config": {
    "size": "<size>",
    "quality": "<quality>",
    "n": <n>,
    "provider": "<provider>"   // omitted if not specified
  }
}
```

### Handling the LLM Response

The LLM Service returns a list of base64-encoded image strings along with provider and model metadata.

For each returned image:

1. Decode the base64 string to raw bytes.
2. Save the original bytes to storage at `{user_id}/{image_id}/original.png`.
3. Call `process_image` to generate WebP variants using the preset resolved from `category`.
4. Save each variant.
5. Insert an `ImageRecord` to MongoDB with `source = "ai_generated"` and metadata containing:
   - `prompt` (from request)
   - `provider` (from LLM response)
   - `model` (from LLM response)
6. Return all created `ImageRecord` objects in the response.

---

## Integration Points

| Direction | Target | Purpose |
|-----------|--------|---------|
| Outbound | LLM Service `POST /generate/image` | AI image generation |
| Inbound | API Gateway `/api/images/*` | All client-facing image requests |

---

## File Structure

```
image-service/
├── Dockerfile
├── requirements.txt
├── app/
│   ├── main.py                      # FastAPI app, lifespan, route registration, middleware
│   ├── config.py                    # ImageConfig: storage_path, max_file_size, llm_service_url
│   ├── database.py                  # MongoDB connection setup and teardown
│   ├── models/
│   │   └── images.py                # ImageRecord, ImageVariant, GenerateRequest, ImageUpdate, PROCESSING_PRESETS
│   ├── routes/
│   │   ├── health.py                # GET /health, GET /health/detailed
│   │   ├── images.py                # Upload, get metadata, serve file, serve variant, delete, update
│   │   ├── user_images.py           # GET /images/user/{user_id}, GET /images/user/{user_id}/{category}
│   │   └── generate.py              # POST /images/generate
│   ├── services/
│   │   └── generation_proxy.py      # Calls LLM Service, decodes base64, saves results to storage + DB
│   ├── processing/
│   │   └── image_processor.py       # validate_image_file, get_image_dimensions, process_image
│   └── storage/
│       ├── base.py                  # StorageBackend protocol definition
│       └── local.py                 # LocalStorage implementation using aiofiles
└── tests/
    ├── conftest.py                  # MockStorage, test image fixture helpers
    ├── unit/
    │   ├── test_models.py           # Pydantic model validation tests
    │   ├── test_processor.py        # Image processing logic tests
    │   └── test_storage.py          # LocalStorage unit tests
    └── integration/
        ├── test_image_routes.py     # Upload, get, serve, delete, update endpoint tests
        ├── test_user_image_routes.py # User listing and category filter endpoint tests
        └── test_generate_routes.py  # AI generation proxy endpoint tests
```
