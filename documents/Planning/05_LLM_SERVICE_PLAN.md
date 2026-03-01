# LLM Service - Planning Document

## 1. Purpose

A generic AI service providing text and image generation through a multi-provider factory pattern. It manages:
- **Text generation** — chat, completion, structured output via LLM providers
- **Image generation** — AI image creation via vision/generation providers
- **Provider factory** — pluggable providers with fallback chains
- **Streaming** — Server-Sent Events (SSE) for real-time text streaming
- **Conversation history** — persistent chat context per user

This service is **application-agnostic** — it generates text/images based on prompts and system instructions. Application-specific behavior (persona, domain knowledge) is injected via system prompts and configuration, not hardcoded.

## 2. Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | Python 3.12 + FastAPI |
| Database | MongoDB (conversations, config) |
| Providers | Anthropic SDK, OpenAI SDK, Google GenAI SDK |
| Streaming | SSE (Server-Sent Events) via sse-starlette |
| Validation | Pydantic v2 |
| Auth | Internal JWT + API key |
| Testing | pytest + httpx |

## 3. Provider Factory Architecture

### 3.1 Provider Capabilities Matrix

| Provider | Text Gen | Image Gen | Video Gen | Streaming | Primary Use |
|----------|----------|-----------|-----------|-----------|-------------|
| Anthropic (Claude) | Yes | No | No | Yes | Primary text |
| OpenAI (GPT-4o) | Yes | Yes (DALL-E) | No | Yes | Backup text + image |
| Google (Gemini) | Yes | Yes (Imagen) | Yes | Yes | Primary image/video |

### 3.2 Factory Pattern

```python
class TextProvider(Protocol):
    async def generate(self, messages: list[Message], config: GenConfig) -> str: ...
    async def stream(self, messages: list[Message], config: GenConfig) -> AsyncIterator[str]: ...

class ImageProvider(Protocol):
    async def generate(self, prompt: str, config: ImageGenConfig) -> bytes: ...

class VideoProvider(Protocol):
    async def generate(self, prompt: str, config: VideoGenConfig) -> bytes: ...

class ProviderFactory:
    def get_text_provider(self, provider: str | None = None) -> TextProvider: ...
    def get_image_provider(self, provider: str | None = None) -> ImageProvider: ...
    def get_video_provider(self, provider: str | None = None) -> VideoProvider: ...
```

### 3.3 Provider Implementations

```python
# Text Providers
class AnthropicTextProvider(TextProvider):       # Claude Sonnet 4
    model = "claude-sonnet-4-20250514"

class OpenAITextProvider(TextProvider):           # GPT-4o
    model = "gpt-4o"

class GeminiTextProvider(TextProvider):           # Gemini 2.0 Flash
    model = "gemini-2.0-flash"

# Image Providers
class OpenAIImageProvider(ImageProvider):         # DALL-E 3
    model = "dall-e-3"

class GeminiImageProvider(ImageProvider):         # Imagen 3
    model = "imagen-3.0-generate-002"

# Video Providers
class GeminiVideoProvider(VideoProvider):         # Veo 2
    model = "veo-002"
```

### 3.4 Provider Configuration (YAML)

```yaml
# config/providers.yml
providers:
  text:
    primary: anthropic
    fallback: openai
    providers:
      anthropic:
        model: claude-sonnet-4-20250514
        max_tokens: 4096
        timeout: 30
      openai:
        model: gpt-4o
        max_tokens: 4096
        timeout: 30
      gemini:
        model: gemini-2.0-flash
        max_tokens: 4096
        timeout: 30

  image:
    primary: gemini
    fallback: openai
    providers:
      gemini:
        model: imagen-3.0-generate-002
        timeout: 60
      openai:
        model: dall-e-3
        timeout: 60
        size: "1024x1024"
        quality: "standard"

  video:
    primary: gemini
    fallback: null
    providers:
      gemini:
        model: veo-002
        timeout: 120
```

### 3.5 Fallback Chain

```
Request → Primary Provider
    │
    ├─ Success → Return result
    │
    └─ Failure (timeout, error, rate limit)
        │
        ├─ Fallback Provider configured?
        │   ├─ Yes → Retry with fallback
        │   │   ├─ Success → Return result
        │   │   └─ Failure → Return error
        │   └─ No → Return error
        │
        └─ Log failure for monitoring
```

## 4. Data Models

### 4.1 Conversation

```python
class Conversation(BaseModel):
    id: str                           # UUID
    user_id: str
    title: str | None                 # Auto-generated or user-set
    system_prompt: str | None         # Injected persona/behavior
    messages: list[Message]
    metadata: dict                    # Flexible app-specific data
    created_at: datetime
    updated_at: datetime

class Message(BaseModel):
    role: str                         # "user" | "assistant" | "system"
    content: str
    timestamp: datetime
    provider: str | None              # Which provider generated this
    model: str | None                 # Which model was used
    tokens_used: int | None           # Token count for this message
```

### 4.2 Generation Config

```python
class TextGenConfig(BaseModel):
    provider: str | None = None       # Override default provider
    model: str | None = None          # Override default model
    max_tokens: int = 4096
    temperature: float = 0.7
    system_prompt: str | None = None
    stream: bool = False

class ImageGenConfig(BaseModel):
    provider: str | None = None
    prompt: str
    negative_prompt: str | None = None
    size: str = "1024x1024"           # "256x256", "512x512", "1024x1024"
    quality: str = "standard"         # "standard" | "hd"
    style: str | None = None          # Provider-specific style hints
    n: int = 1                        # Number of images

class VideoGenConfig(BaseModel):
    provider: str | None = None
    prompt: str
    duration: int = 5                 # Seconds
    aspect_ratio: str = "16:9"
```

### 4.3 Generation Result

```python
class TextResult(BaseModel):
    content: str
    provider: str
    model: str
    tokens_used: int
    finish_reason: str

class ImageResult(BaseModel):
    images: list[GeneratedImage]
    provider: str
    model: str

class GeneratedImage(BaseModel):
    data: bytes | None                # Raw image data
    url: str | None                   # Or URL if provider returns URL
    format: str                       # "png", "jpg"
    size: str                         # "1024x1024"
```

## 5. API Endpoints

### 5.1 Text Generation

| Method | Path | Description |
|--------|------|-------------|
| POST | `/generate/text` | One-shot text generation |
| POST | `/generate/text/stream` | Streaming text generation (SSE) |

### 5.2 Chat (Conversational)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat` | Send message in conversation, get response |
| POST | `/chat/stream` | Send message, stream response (SSE) |
| GET | `/chat/conversations/{user_id}` | List user's conversations |
| GET | `/chat/conversations/{conversation_id}` | Get conversation history |
| DELETE | `/chat/conversations/{conversation_id}` | Delete conversation |
| PATCH | `/chat/conversations/{conversation_id}` | Update title/metadata |

### 5.3 Image Generation

| Method | Path | Description |
|--------|------|-------------|
| POST | `/generate/image` | Generate image from prompt |
| GET | `/generate/image/{generation_id}/status` | Check async generation status |

### 5.4 Video Generation

| Method | Path | Description |
|--------|------|-------------|
| POST | `/generate/video` | Generate video from prompt |
| GET | `/generate/video/{generation_id}/status` | Check async generation status |

### 5.5 Provider Info

| Method | Path | Description |
|--------|------|-------------|
| GET | `/providers` | List available providers and capabilities |
| GET | `/providers/{provider}/status` | Check provider health/availability |

### 5.6 Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health check |
| GET | `/health/detailed` | Health + provider connectivity |

## 6. Key Flows

### 6.1 Chat with Streaming

```
POST /chat/stream
    │  Body: { conversation_id, message, config }
    │
    ├─ Check permission: ai_text_generation (via Permissions Service)
    ├─ Record feature usage
    ├─ Load conversation history from MongoDB
    ├─ Build message list: system_prompt + history + new message
    ├─ Get text provider (primary or specified)
    │
    ├─ Stream response via SSE:
    │   ├─ event: start    → { conversation_id, provider, model }
    │   ├─ event: chunk    → { text: "partial response..." }  (repeated)
    │   ├─ event: end      → { tokens_used, finish_reason }
    │   └─ event: error    → { message, code }  (on failure)
    │
    ├─ Save user message to conversation
    ├─ Save assistant response to conversation
    └─ Update conversation timestamp
```

### 6.2 Image Generation

```
POST /generate/image
    │  Body: { prompt, size, style, provider }
    │
    ├─ Check permission: ai_image_generation
    ├─ Record feature usage
    ├─ Get image provider (Gemini primary, OpenAI fallback)
    ├─ Call provider.generate(prompt, config)
    │   ├─ Success → return image data
    │   └─ Failure → try fallback provider
    │
    ├─ Return: { image_data (base64), provider, model, format }
    │
    └─ Caller (Image Service) handles storage
```

### 6.3 Provider Fallback

```
Request to Anthropic (primary text)
    │
    ├─ Timeout after 30s
    │
    ├─ Log: "[LLM] Anthropic timeout, falling back to OpenAI"
    │
    ├─ Retry with OpenAI
    │   ├─ Success → return with provider="openai"
    │   └─ Failure → return error
    │
    └─ Response includes which provider was actually used
```

## 7. Streaming (SSE) Protocol

```
Content-Type: text/event-stream

event: start
data: {"conversation_id": "abc123", "provider": "anthropic", "model": "claude-sonnet-4"}

event: chunk
data: {"text": "Hello! "}

event: chunk
data: {"text": "How can "}

event: chunk
data: {"text": "I help you today?"}

event: end
data: {"tokens_used": 42, "finish_reason": "stop"}
```

## 8. MongoDB Collections

```
conversations:
  - id (unique)
  - user_id (index)
  - updated_at (index, descending)
  - (user_id, updated_at) compound index

generation_jobs:
  - id (unique)
  - user_id (index)
  - status (index)
  - created_at (index, TTL: 24 hours)
```

## 9. Configuration

```env
# Provider API Keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...

# Provider Config
LLM_CONFIG_PATH=/app/config/providers.yml

# Service URLs
PERMISSIONS_SERVICE_URL=http://permissions:5003

# Defaults
LLM_DEFAULT_TEXT_PROVIDER=anthropic
LLM_DEFAULT_IMAGE_PROVIDER=gemini
LLM_DEFAULT_VIDEO_PROVIDER=gemini
LLM_MAX_CONVERSATION_HISTORY=50     # Messages to include in context
LLM_CONVERSATION_TTL_DAYS=30        # Auto-cleanup old conversations
```

## 10. Security

- All generation endpoints require valid JWT
- Provider API keys stored as environment variables only
- Conversation data scoped to user_id — no cross-user access
- System prompts can only be set by admin or service-to-service calls
- Rate limiting at gateway level + provider-level timeouts
- No user-provided content forwarded to providers without sanitization

## 11. Integration Points

| Service | Direction | Purpose |
|---------|-----------|---------|
| Image Service | ← called by | AI image generation |
| Permissions Service | → calls | Usage checks before generation |
| Node Gateway | ← called by | Client chat/generation requests |

## 12. Testing Strategy

### Unit Tests
- Provider factory initialization and selection
- Fallback chain logic
- Message formatting per provider
- Conversation history management
- SSE event formatting
- Config loading from YAML

### Integration Tests
- Full chat flow (with mocked provider responses)
- Image generation flow (with mocked provider)
- Streaming response validation
- Provider fallback scenarios
- Conversation persistence and retrieval
- Permission check integration (mocked Permissions Service)
