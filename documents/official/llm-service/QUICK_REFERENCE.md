# LLM Service - Quick Reference

## Overview

FastAPI AI service running on **port 5000** with **MongoDB** persistence. Provides multi-provider AI text and image generation with automatic fallback, SSE streaming, and persistent chat conversations.

Supported providers:
- **Anthropic** - Claude (text only)
- **OpenAI** - GPT-4o (text) + DALL-E 3 (image)
- **Google Gemini** - gemini-2.5-flash (text) + Imagen 3 (image)

---

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | None | Service alive check |
| `GET` | `/health/detailed` | None | Check MongoDB + provider availability |
| `POST` | `/generate/text` | API Key/JWT | One-shot text generation |
| `POST` | `/generate/text/stream` | API Key/JWT | SSE streaming text generation |
| `POST` | `/generate/image` | API Key/JWT | Image generation (returns base64) |
| `POST` | `/chat` | API Key/JWT | Send chat message (new or continue conversation) |
| `POST` | `/chat/stream` | API Key/JWT | SSE streaming chat |
| `GET` | `/chat/conversations/{user_id}` | API Key/JWT | List conversations (paginated) |
| `GET` | `/chat/conversations/detail/{conversation_id}` | API Key/JWT | Get full conversation |
| `DELETE` | `/chat/conversations/detail/{conversation_id}` | API Key/JWT | Delete conversation |
| `PATCH` | `/chat/conversations/detail/{conversation_id}` | API Key/JWT | Update title/metadata |
| `GET` | `/providers` | API Key/JWT | List all providers with status |
| `GET` | `/providers/{name}/status` | API Key/JWT | Live health check (makes test API call) |

---

## Providers

| Provider | Text Model | Image Model | Requires |
|----------|------------|-------------|----------|
| Anthropic | `claude-sonnet-4-20250514` | — | `ANTHROPIC_API_KEY` |
| OpenAI | `gpt-4o` | `dall-e-3` | `OPENAI_API_KEY` |
| Gemini | `gemini-2.5-flash` | `imagen-3.0-generate-002` | `GOOGLE_API_KEY` |

---

## Default Provider Configuration

| Capability | Primary | Fallback |
|------------|---------|----------|
| Text generation | `anthropic` | `openai` |
| Image generation | `gemini` | `openai` |

Providers are resolved in order: **requested provider → primary → fallback → any available**.

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `MONGODB_URI` | MongoDB connection string |
| `INTERNAL_API_KEY` | API key for service-to-service auth |
| `JWT_SECRET` | Secret for JWT token verification |
| `ANTHROPIC_API_KEY` | Anthropic provider credentials |
| `OPENAI_API_KEY` | OpenAI provider credentials |
| `GOOGLE_API_KEY` | Google Gemini provider credentials |
| `LLM_CONFIG_PATH` | Path to provider config file (default: `config/providers.yml`) |
| `LLM_MAX_CONVERSATION_HISTORY` | Max messages sent to provider per request (default: `50`) |

---

## SSE Event Format

Streaming endpoints (`/generate/text/stream`, `/chat/stream`) emit Server-Sent Events with JSON-encoded data.

| Event Type | Payload | Description |
|------------|---------|-------------|
| `start` | `{ "event": "start", "provider": "...", "model": "..." }` | Stream begins; identifies which provider/model is responding |
| `chunk` | `{ "event": "chunk", "data": "text content" }` | Incremental text delta |
| `end` | `{ "event": "end" }` | Stream complete |
| `error` | `{ "event": "error", "data": "error message" }` | Stream failed |

### Example SSE Response Sequence

```
data: {"event": "start", "provider": "anthropic", "model": "claude-sonnet-4-20250514"}

data: {"event": "chunk", "data": "Hello"}

data: {"event": "chunk", "data": ", world!"}

data: {"event": "end"}
```

---

## Quick Request Examples

### Text Generation

```json
POST /generate/text
{
  "prompt": "Explain photosynthesis in simple terms.",
  "config": {
    "provider": "anthropic",
    "max_tokens": 512,
    "temperature": 0.7
  }
}
```

### Image Generation

```json
POST /generate/image
{
  "prompt": "A majestic eagle soaring over a mountain range at sunrise.",
  "config": {
    "provider": "gemini",
    "size": "1024x1024",
    "quality": "standard",
    "n": 1
  }
}
```

Returns base64-encoded image data.

### Chat (New Conversation)

```json
POST /chat
{
  "conversation_id": null,
  "message": "What are the rarest animals in North America?",
  "system_prompt": "You are a wildlife expert.",
  "config": {}
}
```

### Chat (Continue Conversation)

```json
POST /chat
{
  "conversation_id": "existing-uuid-here",
  "message": "Tell me more about the California condor.",
  "config": {}
}
```

---

## Auth

All endpoints except `/health` and `/health/detailed` require one of:
- `Authorization: Bearer <jwt_token>` header
- `X-API-Key: <internal_api_key>` header
