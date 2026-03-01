from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    provider: str | None = None
    model: str | None = None
    tokens_used: int | None = None


class Conversation(BaseModel):
    id: str
    user_id: str
    title: str | None = None
    system_prompt: str | None = None
    messages: list[Message] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConversationCreate(BaseModel):
    title: str | None = None
    system_prompt: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationUpdate(BaseModel):
    title: str | None = None
    system_prompt: str | None = None
    metadata: dict[str, Any] | None = None


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str
    system_prompt: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
