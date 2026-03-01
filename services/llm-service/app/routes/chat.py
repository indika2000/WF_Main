import logging

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from sse_starlette.sse import EventSourceResponse

from app.database import get_db
from app.models.conversations import ChatRequest, ConversationUpdate
from app.services import chat_service
from shared.python.auth import get_current_user
from shared.python.responses import error_response, success_response

logger = logging.getLogger("llm")
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
async def send_message(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Send a message and get a response."""
    try:
        result = await chat_service.send_message(
            message=request.message,
            user_id=current_user["uid"],
            db=db,
            conversation_id=request.conversation_id,
            system_prompt=request.system_prompt,
            config=request.config,
        )
        return success_response(data=result)
    except ValueError as e:
        return error_response(
            message=str(e),
            error_code="CHAT_ERROR",
            status_code=400,
        )
    except Exception as e:
        logger.error("Chat error: %s", e, exc_info=True)
        return error_response(
            message="Chat failed",
            error_code="CHAT_ERROR",
            status_code=500,
            detail=str(e),
        )


@router.post("/stream")
async def stream_message(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Stream a chat response via SSE."""
    return EventSourceResponse(
        chat_service.stream_message(
            message=request.message,
            user_id=current_user["uid"],
            db=db,
            conversation_id=request.conversation_id,
            system_prompt=request.system_prompt,
            config=request.config,
        )
    )


@router.get("/conversations/{user_id}")
async def list_conversations(
    user_id: str,
    page: int = 1,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """List conversations for a user."""
    # Allow service calls or matching user
    if current_user["role"] != "service" and current_user["uid"] != user_id:
        return error_response(
            message="Not authorized to view these conversations",
            error_code="FORBIDDEN",
            status_code=403,
        )

    conversations = await chat_service.list_conversations(user_id, db, page, limit)
    return success_response(data=conversations)


@router.get("/conversations/detail/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get a conversation with full message history."""
    conv = await chat_service.get_conversation(conversation_id, current_user["uid"], db)
    if not conv:
        return error_response(
            message="Conversation not found",
            error_code="NOT_FOUND",
            status_code=404,
        )
    return success_response(data=conv)


@router.delete("/conversations/detail/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Delete a conversation."""
    deleted = await chat_service.delete_conversation(conversation_id, current_user["uid"], db)
    if not deleted:
        return error_response(
            message="Conversation not found",
            error_code="NOT_FOUND",
            status_code=404,
        )
    return success_response(message="Conversation deleted")


@router.patch("/conversations/detail/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    updates: ConversationUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Update conversation title, system prompt, or metadata."""
    conv = await chat_service.update_conversation(
        conversation_id,
        current_user["uid"],
        updates.model_dump(exclude_none=True),
        db,
    )
    if not conv:
        return error_response(
            message="Conversation not found",
            error_code="NOT_FOUND",
            status_code=404,
        )
    return success_response(data=conv)
