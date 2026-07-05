# app/api/endpoints/chat.py
"""POST /chat — Answer a question using memories retrieved from Cognee.

Flow:
    1. Validate the incoming question.
    2. Delegate to ``MemoryManager.ask()``.
    3. Return the answer, sources, memories_used, and memory_trace.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.api.schemas.chat_models import (
    ChatRequest,
    ChatResponse,
    MemoryTraceItem,
    SourceItem,
)
from app.services.cognee.memory_manager import MemoryManager
from app.services.llm.llm_client import LLMClient
from app.services.llm.prompts import CONTEXT_ENGINE_PROMPT

logger = logging.getLogger(__name__)
router = APIRouter()

# Singleton manager — stateless, safe to share between requests.
_memory_manager = MemoryManager()


@router.get("/")
async def get_chat_history():
    """Returns initial/history chat messages for testing or default view."""
    return {
        "messages": [
            {"role": "assistant", "content": "Hello! I am Chronos AI. How can I help you today?"}
        ]
    }


@router.post("/", response_model=ChatResponse)
async def process_chat_message(payload: ChatRequest) -> ChatResponse:
    """Answer a user question using Cognee's persistent news memory."""
    question = payload.message.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Message content cannot be blank.")

    logger.info("Chat request received — question: %.100r", question)

    try:
        result = await _memory_manager.ask(question)
    except Exception as exc:
        logger.exception("Unexpected error in MemoryManager.ask().")
        raise HTTPException(
            status_code=500,
            detail=f"Internal memory retrieval error: {exc}",
        ) from exc

    # Coerce raw dicts from AskResult into Pydantic models
    sources = [SourceItem(**s) for s in result.sources]
    memory_trace = [MemoryTraceItem(**t) for t in result.memory_trace]

    return ChatResponse(
        status="success",
        response=result.answer,
        sources=sources,
        memories_used=result.memories_used,
        memory_trace=memory_trace,
    )


@router.post("/stream")
async def process_chat_stream(payload: ChatRequest):
    """Answers a user question using a streamed response from the LLM."""
    try:
        user_message = payload.message.strip()
        if not user_message:
            raise HTTPException(status_code=400, detail="Message content cannot be blank.")

        conversation_id = _derive_conversation_id(payload)

        # 1. We could log/persist the user message to memory here if needed
        # await _memory_manager.remember_context(user_message, conversation_id)

        # 2. Get grounded context for the question
        # We reuse MemoryManager's logic for context building (internal call)
        # Note: We might want a public method for this, but for now we follow the remote pattern
        from app.services.cognee.recall import recall_memories
        from app.services.retrieval.context_builder import build_context_prompt, get_system_prompt
        
        memories = await recall_memories(user_message, limit=8)
        context_prompt = build_context_prompt(user_message, memories)
        system_prompt = get_system_prompt()

        # 3. Stream from LLM
        async def event_generator():
            llm = LLMClient()
            full_response_parts = []
            try:
                # Note: generate_stream assumes a method exists in LLMClient
                async for chunk in llm.generate_stream(context_prompt, system_prompt):
                    full_response_parts.append(chunk)
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"

                # PERSISTENCE: This part could be used to remember the assistant response
                # full_response = "".join(full_response_parts)
            except Exception as ex:
                logger.exception("Error in chat stream event generator")
                yield f"data: {json.dumps({'error': str(ex)})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Streaming chat setup failed")
        raise HTTPException(status_code=500, detail=str(e))


def _derive_conversation_id(payload: ChatRequest) -> str:
    if not payload.history:
        return "default"
    content_concat = "".join(m.content for m in payload.history)
    return f"conv_{abs(hash(content_concat))}"
