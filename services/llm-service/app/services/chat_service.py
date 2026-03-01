import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.providers.factory import provider_factory

logger = logging.getLogger("llm")


async def send_message(
    message: str,
    user_id: str,
    db: AsyncIOMotorDatabase,
    conversation_id: str | None = None,
    system_prompt: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send a message in a conversation. Creates conversation if needed.

    Returns dict with conversation_id, response content, and provider info.
    """
    config = config or {}
    now = datetime.now(timezone.utc)

    # Get or create conversation
    if conversation_id:
        conv = await db.conversations.find_one({"_id": conversation_id, "user_id": user_id})
        if not conv:
            raise ValueError(f"Conversation {conversation_id} not found")
    else:
        conversation_id = str(uuid.uuid4())
        conv = {
            "_id": conversation_id,
            "user_id": user_id,
            "title": message[:100],
            "system_prompt": system_prompt,
            "messages": [],
            "metadata": {},
            "created_at": now,
            "updated_at": now,
        }
        await db.conversations.insert_one(conv)

    # Build message list for the provider
    messages = _build_messages(conv, message, system_prompt)

    # Generate response
    provider = provider_factory.get_text_provider(config.get("provider"))
    if not provider:
        raise ValueError("No text provider available")

    try:
        result = await provider.generate(
            messages=messages,
            max_tokens=config.get("max_tokens", 4096),
            temperature=config.get("temperature", 0.7),
        )
    except Exception as e:
        logger.warning("Chat generation failed with %s: %s", provider.name, e)
        fallback = provider_factory.get_fallback_text_provider(provider.name)
        if not fallback:
            raise
        logger.info("Falling back to %s for chat", fallback.name)
        provider = fallback
        result = await provider.generate(
            messages=messages,
            max_tokens=config.get("max_tokens", 4096),
            temperature=config.get("temperature", 0.7),
        )

    # Save both messages to conversation
    user_msg = {
        "role": "user",
        "content": message,
        "timestamp": now,
    }
    assistant_msg = {
        "role": "assistant",
        "content": result["content"],
        "timestamp": datetime.now(timezone.utc),
        "provider": provider.name,
        "model": provider.model,
        "tokens_used": result["tokens_used"],
    }

    await db.conversations.update_one(
        {"_id": conversation_id},
        {
            "$push": {"messages": {"$each": [user_msg, assistant_msg]}},
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
    )

    return {
        "conversation_id": conversation_id,
        "content": result["content"],
        "provider": provider.name,
        "model": provider.model,
        "tokens_used": result["tokens_used"],
        "finish_reason": result["finish_reason"],
    }


async def stream_message(
    message: str,
    user_id: str,
    db: AsyncIOMotorDatabase,
    conversation_id: str | None = None,
    system_prompt: str | None = None,
    config: dict[str, Any] | None = None,
) -> AsyncIterator[str]:
    """Stream a chat response. Yields SSE-formatted event strings."""
    config = config or {}
    now = datetime.now(timezone.utc)

    # Get or create conversation
    if conversation_id:
        conv = await db.conversations.find_one({"_id": conversation_id, "user_id": user_id})
        if not conv:
            yield json.dumps({"event": "error", "data": "Conversation not found"})
            return
    else:
        conversation_id = str(uuid.uuid4())
        conv = {
            "_id": conversation_id,
            "user_id": user_id,
            "title": message[:100],
            "system_prompt": system_prompt,
            "messages": [],
            "metadata": {},
            "created_at": now,
            "updated_at": now,
        }
        await db.conversations.insert_one(conv)

    messages = _build_messages(conv, message, system_prompt)

    provider = provider_factory.get_text_provider(config.get("provider"))
    if not provider:
        yield json.dumps({"event": "error", "data": "No text provider available"})
        return

    yield json.dumps({
        "event": "start",
        "conversation_id": conversation_id,
        "provider": provider.name,
        "model": provider.model,
    })

    full_response = []
    try:
        async for chunk in provider.stream(
            messages=messages,
            max_tokens=config.get("max_tokens", 4096),
            temperature=config.get("temperature", 0.7),
        ):
            full_response.append(chunk)
            yield json.dumps({"event": "chunk", "data": chunk})

        yield json.dumps({"event": "end"})
    except Exception as e:
        logger.warning("Chat stream failed with %s: %s", provider.name, e)
        yield json.dumps({"event": "error", "data": str(e)})
        return

    # Save messages after successful stream
    user_msg = {
        "role": "user",
        "content": message,
        "timestamp": now,
    }
    assistant_msg = {
        "role": "assistant",
        "content": "".join(full_response),
        "timestamp": datetime.now(timezone.utc),
        "provider": provider.name,
        "model": provider.model,
    }

    await db.conversations.update_one(
        {"_id": conversation_id},
        {
            "$push": {"messages": {"$each": [user_msg, assistant_msg]}},
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
    )


async def list_conversations(
    user_id: str,
    db: AsyncIOMotorDatabase,
    page: int = 1,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """List conversations for a user (without full message history)."""
    skip = (page - 1) * limit
    cursor = db.conversations.find(
        {"user_id": user_id},
        {"messages": 0},  # Exclude messages for listing
    ).sort("updated_at", -1).skip(skip).limit(limit)

    results = []
    async for doc in cursor:
        doc["id"] = doc.pop("_id")
        results.append(doc)
    return results


async def get_conversation(
    conversation_id: str,
    user_id: str,
    db: AsyncIOMotorDatabase,
) -> dict[str, Any] | None:
    """Get a conversation with full message history."""
    doc = await db.conversations.find_one({"_id": conversation_id, "user_id": user_id})
    if doc:
        doc["id"] = doc.pop("_id")
    return doc


async def delete_conversation(
    conversation_id: str,
    user_id: str,
    db: AsyncIOMotorDatabase,
) -> bool:
    """Delete a conversation. Returns True if deleted."""
    result = await db.conversations.delete_one({"_id": conversation_id, "user_id": user_id})
    return result.deleted_count > 0


async def update_conversation(
    conversation_id: str,
    user_id: str,
    updates: dict[str, Any],
    db: AsyncIOMotorDatabase,
) -> dict[str, Any] | None:
    """Update conversation metadata (title, system_prompt, metadata)."""
    allowed_fields = {"title", "system_prompt", "metadata"}
    set_fields = {k: v for k, v in updates.items() if k in allowed_fields and v is not None}
    if not set_fields:
        return await get_conversation(conversation_id, user_id, db)

    set_fields["updated_at"] = datetime.now(timezone.utc)

    await db.conversations.update_one(
        {"_id": conversation_id, "user_id": user_id},
        {"$set": set_fields},
    )
    return await get_conversation(conversation_id, user_id, db)


def _build_messages(
    conv: dict[str, Any],
    new_message: str,
    system_prompt: str | None = None,
) -> list[dict[str, str]]:
    """Build the message list for the provider from conversation history."""
    messages: list[dict[str, str]] = []

    # System prompt (prefer request-level, then conversation-level)
    sys_prompt = system_prompt or conv.get("system_prompt")
    if sys_prompt:
        messages.append({"role": "system", "content": sys_prompt})

    # Historical messages (trim to limit)
    history = conv.get("messages", [])
    max_history = settings.llm_max_conversation_history
    if len(history) > max_history:
        history = history[-max_history:]

    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # New user message
    messages.append({"role": "user", "content": new_message})
    return messages
