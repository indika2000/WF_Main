# Image Service - Planning Document

## 1. Purpose

A generic image management service handling:
- **Upload & storage** — accept image uploads, store organized by user/context
- **Processing** — auto-generate thumbnails, resize variants, format conversion
- **Serving** — serve images via HTTP with caching headers
- **AI generation** — proxy to LLM Service for AI-generated images
- **Metadata** — track image records, tags, associations in MongoDB

This service is **application-agnostic** — it manages images as generic assets with flexible metadata. Application-specific meaning (e.g., "this is a card image") is stored in metadata, not hardcoded.

## 2. Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | Python 3.12 + FastAPI |
| Database | MongoDB (metadata) |
| Storage | Local filesystem (Docker volume), S3-ready interface |
| Processing | Pillow (PIL) |
| Validation | Pydantic v2 |
| Auth | Internal JWT + API key |
| Testing | pytest + httpx |

## 3. Storage Architecture

### 3.1 Directory Structure

```
storage/                              # Docker volume mount
├── uploads/                          # Original uploaded files
│   └── {user_id}/
│       ├── {category}/               # e.g., "profile", "collection", "general"
│       │   └── {uuid}.{ext}
│       └── ...
├── processed/                        # Generated variants
│   └── {user_id}/
│       └── {category}/
│           ├── {uuid}_thumb.{ext}    # Thumbnail
│           ├── {uuid}_medium.{ext}   # Medium
│           └── {uuid}_large.{ext}    # Large
├── generated/                        # AI-generated images
│   └── {user_id}/
│       └── {uuid}.{ext}
└── static/                           # App-bundled static assets
    └── {category}/
        └── {filename}
```

### 3.2 Storage Interface (S3-Ready)

```python
class StorageBackend(Protocol):
    async def save(self, path: str, data: bytes) -> str: ...
    async def load(self, path: str) -> bytes: ...
    async def delete(self, path: str) -> bool: ...
    async def exists(self, path: str) -> bool: ...
    async def get_url(self, path: str) -> str: ...

class LocalStorage(StorageBackend): ...     # Docker volume
class S3Storage(StorageBackend): ...        # Future: AWS S3
```

Configuration selects backend:
```
IMAGE_STORAGE_BACKEND=local   # or "s3"
IMAGE_STORAGE_PATH=/storage   # local path or bucket name
```

## 4. Data Models

### 4.1 ImageRecord

```python
class ImageRecord(BaseModel):
    id: str                           # UUID
    user_id: str                      # Owner
    category: str                     # "profile", "collection", "general", etc.
    filename: str                     # Original filename
    content_type: str                 # MIME type
    file_size: int                    # Bytes
    width: int | None                 # Pixels
    height: int | None                # Pixels
    storage_path: str                 # Path in storage backend
    variants: dict[str, ImageVariant] # Generated variants
    source: str                       # "upload" | "ai_generated" | "system"
    metadata: dict                    # Flexible app-specific data
    tags: list[str]                   # Searchable tags
    created_at: datetime
    updated_at: datetime

class ImageVariant(BaseModel):
    size_name: str                    # "thumb", "medium", "large"
    storage_path: str
    width: int
    height: int
    file_size: int
```

### 4.2 Processing Presets

```python
PROCESSING_PRESETS = {
    "profile": {
        "thumb":  { "width": 100,  "height": 100,  "crop": "center" },
        "medium": { "width": 300,  "height": 300,  "crop": "center" },
    },
    "card": {
        "thumb":  { "width": 150,  "height": 210,  "crop": "center" },
        "medium": { "width": 300,  "height": 420,  "crop": "center" },
        "large":  { "width": 600,  "height": 840,  "crop": "center" },
    },
    "general": {
        "thumb":  { "width": 200,  "height": 200,  "crop": "fit" },
        "medium": { "width": 600,  "height": 600,  "crop": "fit" },
        "large":  { "width": 1200, "height": 1200, "crop": "fit" },
    },
}
```

## 5. API Endpoints

### 5.1 Upload & Management

| Method | Path | Description |
|--------|------|-------------|
| POST | `/images/upload` | Upload image(s) with category and metadata |
| GET | `/images/{image_id}` | Get image metadata/record |
| GET | `/images/{image_id}/file` | Serve original image file |
| GET | `/images/{image_id}/file/{variant}` | Serve specific variant (thumb, medium, large) |
| DELETE | `/images/{image_id}` | Delete image and all variants |
| PATCH | `/images/{image_id}` | Update metadata, tags |

### 5.2 User Images

| Method | Path | Description |
|--------|------|-------------|
| GET | `/images/user/{user_id}` | List user's images (paginated, filterable) |
| GET | `/images/user/{user_id}/{category}` | List user's images in a category |
| DELETE | `/images/user/{user_id}/{category}` | Delete all images in a category |

### 5.3 Processing

| Method | Path | Description |
|--------|------|-------------|
| POST | `/images/{image_id}/process` | Re-process image with specified preset |
| POST | `/images/{image_id}/transform` | Apply transform (rotate, crop, resize) |

### 5.4 AI Generation (Proxy to LLM Service)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/images/generate` | Generate image via AI (proxied to LLM Service) |
| GET | `/images/generate/{generation_id}/status` | Check generation status |

### 5.5 Static Assets

| Method | Path | Description |
|--------|------|-------------|
| GET | `/static/{category}/{filename}` | Serve static app assets |

### 5.6 Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health check |
| GET | `/health/detailed` | Detailed health (MongoDB, storage, disk space) |

## 6. Key Flows

### 6.1 Image Upload

```
POST /images/upload
    │  Form data: file, category, metadata (JSON)
    │
    ├─ Validate file type (png, jpg, webp, gif)
    ├─ Validate file size (max 10MB default, configurable)
    ├─ Generate UUID for image
    ├─ Save original to storage: uploads/{user_id}/{category}/{uuid}.{ext}
    ├─ Read image dimensions
    ├─ Look up processing preset for category
    ├─ Generate all variants (async, in background)
    │   ├─ Resize to each variant size
    │   ├─ Save to: processed/{user_id}/{category}/{uuid}_{variant}.{ext}
    │   └─ Record variant metadata
    ├─ Create ImageRecord in MongoDB
    └─ Return: { id, variants, urls }
```

### 6.2 AI Image Generation

```
POST /images/generate
    │  Body: { prompt, style, size, user_id }
    │
    ├─ Check permission: ai_image_generation (via Permissions Service)
    ├─ Record feature usage (via Permissions Service)
    ├─ Forward to LLM Service: POST /generate/image
    │   └─ LLM Service calls provider (Gemini/OpenAI)
    │
    ├─ Receive generated image data
    ├─ Save to storage: generated/{user_id}/{uuid}.png
    ├─ Process variants using "general" preset
    ├─ Create ImageRecord with source="ai_generated"
    └─ Return: { id, variants, urls }
```

### 6.3 Image Serving

```
GET /images/{image_id}/file/{variant}
    │
    ├─ Look up ImageRecord
    ├─ Get variant storage path
    ├─ Load from storage backend
    ├─ Set cache headers (Cache-Control: max-age=3600)
    └─ Stream file response with correct Content-Type
```

## 7. MongoDB Collections

```
images:
  - id (unique)
  - user_id (index)
  - (user_id, category) compound index
  - tags (index, multikey)
  - created_at (index, descending)
  - source (index)
```

## 8. Configuration

```env
# Storage
IMAGE_STORAGE_BACKEND=local
IMAGE_STORAGE_PATH=/storage
IMAGE_MAX_FILE_SIZE=10485760          # 10MB in bytes
IMAGE_ALLOWED_TYPES=png,jpg,jpeg,webp,gif

# Processing
IMAGE_JPEG_QUALITY=85
IMAGE_WEBP_QUALITY=80
IMAGE_PNG_COMPRESSION=6

# Service URLs
LLM_SERVICE_URL=http://llm-service:5000
PERMISSIONS_SERVICE_URL=http://permissions:5003
```

## 9. Security

- All uploads authenticated via JWT
- Users can only access their own images (unless image is marked public)
- File type validation on upload (magic bytes, not just extension)
- File size limits enforced server-side
- No path traversal — all paths constructed from UUIDs
- Static assets are publicly accessible (no auth required)
- Rate limiting on upload endpoints

## 10. Integration Points

| Service | Direction | Purpose |
|---------|-----------|---------|
| LLM Service | → calls | AI image generation |
| Permissions Service | → calls | Check ai_image_generation permission, record usage |
| Node Gateway | ← called by | All client requests |

## 11. Docker Volume

```yaml
# In docker-compose.yml
image-service:
  volumes:
    - image-storage:/storage          # Persistent storage
    - ./image-service/app:/app        # Hot-reload

volumes:
  image-storage:                      # Named volume, persists across restarts
```

## 12. Testing Strategy

### Unit Tests
- Upload validation (file type, size, dimensions)
- Processing preset application
- Variant generation logic
- Storage backend interface (mock filesystem)
- Metadata CRUD

### Integration Tests
- Full upload → process → serve flow
- AI generation proxy flow (LLM Service mocked)
- Permission checks on upload and generation
- Category-based image listing and filtering
- Image deletion (cascades to variants)
