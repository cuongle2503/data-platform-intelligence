from __future__ import annotations

import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from services.ai.pipeline.orchestrator import rag_pipeline
from services.shared.database import DatabasePool
import uuid

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/api/chat", tags=["chat"])

class ChatRequest(BaseModel):
    query: str
    session_id: str | None = None

async def save_message(session_id: str | None, role: str, content: str):
    """Save message to database and return session_id."""
    pool = DatabasePool.get_pool()
    session_uuid = None

    if session_id:
        try:
            session_uuid = uuid.UUID(session_id)
        except ValueError:
            session_uuid = None

    if not session_uuid:
        session_uuid = uuid.uuid4()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO chat.sessions (id, title) VALUES ($1, $2)",
                session_uuid, f"Chat {str(session_uuid)[:8]}"
            )

    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO chat.messages (session_id, role, content) VALUES ($1, $2, $3)",
            session_uuid, role, content
        )
    return str(session_uuid)

@router.post("")
@limiter.limit("5/minute")
async def rest_chat(request: Request, chat_request: ChatRequest):
    """REST fallback endpoint for chat."""
    # Save user message
    session_id = await save_message(chat_request.session_id, 'user', chat_request.query)

    full_response = ""
    async for chunk in rag_pipeline.process_query_stream(chat_request.query):
        full_response += chunk

    # Save assistant message
    await save_message(session_id, 'assistant', full_response)

    return {"session_id": session_id, "query": chat_request.query, "response": full_response}
