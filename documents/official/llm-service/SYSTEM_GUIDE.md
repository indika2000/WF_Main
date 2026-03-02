# LLM Service - System Guide

## Table of Contents

1. [Data Models](#data-models)
2. [Provider Factory Architecture](#provider-factory-architecture)
3. [Individual Providers](#individual-providers)
4. [SSE Streaming](#sse-streaming)
5. [Chat Service](#chat-service)
6. [Config File](#config-file-configprovidersynl)
7. [File Structure](#file-structure)

---

## Data Models

### Message

Represents a single message within a conversation.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `role` | `"user" \| "assistant" \| "system"` | Yes | Who authored the message |
| `content` | `str` | Yes | The message text |
| `timestamp` | `datetime` | Yes | When the message was created |
| `provider` | `str` | No | Which AI provider generated this message (assistant messages) |
| `model` | `str` | No | Which model generated this message (assistant messages) |
| `tokens_used` | `int` | No | Token count for this message (assistant messages) |

---

### Conversation

Stored in MongoDB collection: **`conversations`**

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` (uuid4) | Unique conversation identifier |
| `user_id` | `str` | Owner of the conversation |
| `title` | `str` | Auto-generated from first message (`message[:100]`) |
| `system_prompt` | `str \| None` | Optional persistent system prompt for this conversation |
| `messages` | `Message[]` | Ordered list of all messages |
| `metadata` | `dict` | Arbitrary key-value metadata (patchable) |
| `created_at` | `datetime` | When the conversation was first created |
| `updated_at` | `datetime` | When the conversation was last modified |

---

### TextGenConfig

Configuration for a text generation request.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `provider` | `str \| None` | `None` | Specific provider to use (falls back to config default) |
| `model` | `str \| None` | `None` | Override the model for the chosen provider |
| `max_tokens` | `int` | `4096` | Maximum tokens to generate |
| `temperature` | `float` | `0.7` | Sampling temperature (0.0 = deterministic, 1.0 = creative) |
| `system_prompt` | `str \| None` | `None` | Optional system-level instruction |

---

### TextGenRequest

| Field | Type | Description |
|-------|------|-------------|
| `prompt` | `str` | The user prompt to generate a response for |
| `config` | `TextGenConfig` | Generation configuration |

---

### ImageGenConfig

Configuration for an image generation request.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `provider` | `str \| None` | `None` | Specific provider to use |
| `size` | `str` | `"1024x1024"` | Output image dimensions |
| `quality` | `str` | `"standard"` | Image quality level (`standard` or `hd`) |
| `style` | `str \| None` | `None` | Optional style hint (provider-dependent) |
| `n` | `int` | `1` | Number of images to generate |

---

### ImageGenRequest

| Field | Type | Description |
|-------|------|-------------|
| `prompt` | `str` | Text description of the image to generate |
| `config` | `ImageGenConfig` | Image generation configuration |

Returns a list of image results, each containing:
- `data` - Base64-encoded image bytes
- `format` - Image format string (e.g., `"png"`)
- `size` - Dimensions of the generated image

---

### ChatRequest

| Field | Type | Description |
|-------|------|-------------|
| `conversation_id` | `str \| None` | Existing conversation ID, or `null` to start a new conversation |
| `message` | `str` | The user's message text |
| `system_prompt` | `str \| None` | Request-level system prompt (overrides conversation-level if set) |
| `config` | `dict` | Provider/model overrides, passed through as `TextGenConfig` fields |

---

## Provider Factory Architecture

### Initialization

The `provider_factory` is a singleton initialized during the FastAPI application **lifespan** event (startup). It:

1. Reads `config/providers.yml` (or the path set by `LLM_CONFIG_PATH`)
2. Inspects environment variables for available API keys
3. Instantiates only the providers whose keys are present
4. Makes the factory available to all route handlers via dependency injection or direct import

### providers.yml Role

The config file defines the routing strategy for both text and image generation:
- Which provider is the **primary** (first choice)
- Which provider is the **fallback** (used if primary is unavailable or fails)
- Per-provider settings (model, max_tokens, timeout)

### Provider Resolution Order

When a request arrives, the factory resolves a provider using this priority chain:

```
1. Requested provider (from request body config.provider)
      |
      v
2. Primary provider (from providers.yml text.primary or image.primary)
      |
      v
3. Fallback provider (from providers.yml text.fallback or image.fallback)
      |
      v
4. Any available instantiated provider
```

If no provider can be resolved, a 503 error is returned.

### Runtime Fallback

The `generation_service` wraps provider calls in try/except logic:

- If the **primary** provider raises an exception during generation (network error, rate limit, API failure), the service logs a `WARNING` and automatically retries with the **fallback** provider.
- Fallback errors are not silently swallowed — if the fallback also fails, the exception propagates to the caller as a 500 error.

---

## Individual Providers

All text providers implement a common interface:

```
generate(messages, max_tokens, temperature) -> { content, tokens_used, finish_reason }
stream(messages, max_tokens, temperature) -> AsyncIterator[str]
```

All image providers implement:

```
generate(prompt, size, quality, n) -> [{ data (base64), format, size }]
```

---

### Anthropic Provider (Text Only)

File: `app/providers/anthropic_provider.py`

**System message handling:** Anthropic's API requires system prompts to be passed as a dedicated `system` parameter rather than as a message in the messages array. The provider filters `system` role messages out of the messages list and passes their content separately.

**Streaming:** Uses `client.messages.stream()` context manager to yield content deltas.

**Response structure:**
```python
{
    "content": "...",           # Full generated text
    "tokens_used": 123,         # Input + output tokens
    "finish_reason": "end_turn" # Stop reason from API
}
```

---

### OpenAI Provider (Text + Image)

File: `app/providers/openai_provider.py`

**Text generation:** Uses the standard `chat.completions.create` endpoint. System messages are passed normally in the messages array (OpenAI supports the `system` role natively).

**Streaming:** Uses `chat.completions.create(stream=True)` and yields `choice.delta.content` from each chunk.

**Image generation:** Uses DALL-E 3 with `response_format="b64_json"` so image bytes are returned directly in the API response rather than as a URL. This avoids a secondary download step.

**Response structure (image):**
```python
[{
    "data": "<base64-encoded-png>",
    "format": "png",
    "size": "1024x1024"
}]
```

---

### Gemini Provider (Text + Image)

File: `app/providers/gemini_provider.py`

**Message format:** Gemini uses its own content format. The provider converts standard `Message` objects into `types.Content` and `types.Part` objects from the Google GenAI SDK.

**Critical:** When constructing parts, keyword arguments are required:
```python
# Correct
types.Part.from_text(text="your content here")

# Incorrect - will raise TypeError
types.Part.from_text("your content here")
```

**Text generation:** Uses `client.aio.models.generate_content` (async).

**Image generation:** Uses `client.aio.models.generate_images` with the Imagen model (`imagen-3.0-generate-002`). Returns base64-encoded image data.

---

## SSE Streaming

### Implementation

Streaming endpoints use `sse-starlette`'s `EventSourceResponse`, which wraps an async generator function. The generator yields event dictionaries that `EventSourceResponse` serializes into the SSE wire format.

```python
async def stream_generator():
    yield {"data": json.dumps({"event": "start", "provider": "anthropic", "model": "claude-sonnet-4-20250514"})}
    async for chunk in provider.stream(messages, max_tokens, temperature):
        yield {"data": json.dumps({"event": "chunk", "data": chunk})}
    yield {"data": json.dumps({"event": "end"})}

return EventSourceResponse(stream_generator())
```

### Event Types

| Event | JSON Shape | When Emitted |
|-------|-----------|--------------|
| `start` | `{"event": "start", "provider": "...", "model": "..."}` | Once, immediately before first chunk |
| `chunk` | `{"event": "chunk", "data": "text delta"}` | Once per content delta from the provider |
| `end` | `{"event": "end"}` | Once, after the last chunk |
| `error` | `{"event": "error", "data": "error message"}` | On exception; stream terminates |

### Chat Streaming Persistence

For `/chat/stream`, the accumulated response is saved to MongoDB **after the stream completes**:

1. Stream all chunks to the client
2. Concatenate chunks into a full `assistant` message
3. `$push` both the user message and assistant message onto the conversation's `messages` array in a single MongoDB update
4. Update `updated_at` on the conversation document

This means the conversation is not persisted mid-stream — if the client disconnects early or an error occurs after streaming begins, the messages may not be saved.

---

## Chat Service

File: `app/services/chat_service.py`

### New Conversation Flow

When `conversation_id` is `null` in a `ChatRequest`:

1. Generate a new `uuid4` as the conversation ID
2. Set `title = message[:100]` (truncated first message)
3. Apply `system_prompt` from the request if provided
4. Insert the new `Conversation` document into MongoDB
5. Proceed with generation as normal

### Continuing a Conversation

When `conversation_id` is provided:

1. Fetch the existing conversation from MongoDB
2. Verify ownership: `conversation.user_id == requesting_uid` or requester has role `"service"`
3. Append the new user message to the in-memory message list
4. Trim to the last `LLM_MAX_CONVERSATION_HISTORY` (default: 50) messages before sending to the provider
5. Generate response
6. Persist both user and assistant messages via `$push`

### History Trimming

To avoid exceeding context windows:

```python
history_limit = int(os.environ.get("LLM_MAX_CONVERSATION_HISTORY", 50))
messages_to_send = conversation.messages[-history_limit:]
```

The full history is always preserved in MongoDB — trimming only affects what is sent to the AI provider.

### System Prompt Priority

System prompts are resolved in this order (highest priority first):

1. `system_prompt` from the current `ChatRequest` (request-level)
2. `system_prompt` stored on the `Conversation` document (conversation-level)
3. `system_prompt` from `TextGenConfig` within `config` (config-level)
4. None

### Message Persistence

After a successful (non-streaming) response:

```python
await db.conversations.update_one(
    {"id": conversation_id},
    {
        "$push": {
            "messages": {
                "$each": [user_message.dict(), assistant_message.dict()]
            }
        },
        "$set": {"updated_at": datetime.utcnow()}
    }
)
```

### Ownership Enforcement

All conversation operations (list, get, delete, patch) enforce that:
- The authenticated user's `uid` matches `conversation.user_id`, **OR**
- The authenticated caller has role `"service"` (for internal service-to-service calls)

Violations return HTTP 403.

---

## Config File (config/providers.yml)

```yaml
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
      model: gemini-2.5-flash
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
      quality: standard
```

The `LLM_CONFIG_PATH` environment variable overrides the default path of `config/providers.yml`. This is useful for testing or deploying with alternate configurations without rebuilding the container.

---

## File Structure

```
llm-service/
├── Dockerfile
├── requirements.txt
├── config/
│   └── providers.yml                   # Provider routing and model config
├── app/
│   ├── main.py                         # FastAPI app, lifespan, provider factory init
│   ├── config.py                       # LLMConfig extends BaseServiceConfig
│   ├── database.py                     # MongoDB connection and collection accessors
│   ├── models/
│   │   ├── generation.py               # TextGenConfig/Request, ImageGenConfig/Request, result types
│   │   ├── conversation.py             # Message, Conversation, ChatRequest
│   │   └── providers.py                # ProviderInfo (used by /providers endpoints)
│   ├── routes/
│   │   ├── health.py                   # GET /health, GET /health/detailed
│   │   ├── generate.py                 # POST /generate/text, /generate/text/stream, /generate/image
│   │   ├── chat.py                     # POST /chat, /chat/stream, GET/DELETE/PATCH /chat/conversations/*
│   │   └── providers.py                # GET /providers, GET /providers/{name}/status
│   ├── services/
│   │   ├── generation_service.py       # Text + image generation with fallback logic
│   │   └── chat_service.py             # Conversation CRUD + message handling
│   └── providers/
│       ├── factory.py                  # ProviderFactory singleton, config loading, resolution
│       ├── anthropic_provider.py       # Anthropic Claude (text only)
│       ├── openai_provider.py          # OpenAI GPT-4o + DALL-E 3
│       └── gemini_provider.py          # Google Gemini + Imagen 3
└── tests/
    ├── conftest.py                     # MockTextProvider, MockImageProvider, SSE reset fixture
    ├── unit/
    │   ├── test_models.py              # Pydantic model validation tests
    │   ├── test_providers.py           # Provider unit tests (mocked API calls)
    │   └── test_services.py            # generation_service and chat_service unit tests
    └── integration/
        ├── test_generate_routes.py     # /generate/* route integration tests
        ├── test_chat_routes.py         # /chat/* route integration tests
        └── test_provider_routes.py     # /providers/* route integration tests
```

### Key Module Responsibilities

**`app/main.py`**
- Creates the FastAPI application instance
- Registers all route modules
- Defines the lifespan context manager that initializes `provider_factory` on startup and tears it down on shutdown

**`app/config.py`**
- `LLMConfig` reads all `LLM_*` environment variables
- Extends a shared `BaseServiceConfig` that handles `MONGODB_URI`, `INTERNAL_API_KEY`, and `JWT_SECRET`

**`app/database.py`**
- Establishes the async MongoDB connection using Motor
- Exposes collection accessors used by the chat service

**`app/providers/factory.py`**
- `ProviderFactory` class with `get_text_provider(name=None)` and `get_image_provider(name=None)` methods
- Applies the resolution order: requested → primary → fallback → any
- Raises `NoAvailableProviderError` (caught by routes as 503) if no provider can be resolved

**`app/services/generation_service.py`**
- `generate_text(request)` and `stream_text(request)` for one-shot use
- `generate_image(request)` for image generation
- Handles the primary-to-fallback retry on runtime provider failure

**`app/services/chat_service.py`**
- `send_message(chat_request, user_id)` for non-streaming chat
- `stream_message(chat_request, user_id)` returns an async generator for SSE
- `list_conversations(user_id, page, page_size)` with pagination
- `get_conversation(conversation_id, requesting_uid)` with ownership check
- `delete_conversation(conversation_id, requesting_uid)` with ownership check
- `update_conversation(conversation_id, requesting_uid, title, metadata)` for PATCH

### Test Fixtures

**`conftest.py`** provides:
- `MockTextProvider` - in-memory implementation of the text provider interface, returns configurable canned responses
- `MockImageProvider` - in-memory implementation of the image provider interface, returns fake base64 data
- SSE reset fixture - clears SSE state between tests to prevent event bleed across test cases
