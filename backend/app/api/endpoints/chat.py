# app/api/endpoints/chat.py
"""POST /chat — Answer a question using memories retrieved from Cognee.

Flow:
    1. Validate the incoming question.
    2. Delegate to ``MemoryManager.ask()``.
    3. Return the answer, sources, memories_used, and memory_trace.

No LLM calls, no Cognee calls, no prompt logic live here.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.api.schemas.chat_models import (
    ChatRequest,
    ChatResponse,
    MemoryTraceItem,
    SourceItem,
)
from app.services.cognee.memory_manager import MemoryManager

logger = logging.getLogger(__name__)

router = APIRouter()

# Singleton manager — stateless, safe to share between requests.
_memory_manager = MemoryManager()


@router.post("/", response_model=ChatResponse)
async def process_chat_message(payload: ChatRequest) -> ChatResponse:
    """Answer a user question using Cognee's persistent news memory.

    The response always contains:
    - **response**: the LLM answer grounded in retrieved memories.
    - **sources**: deduplicated article citations.
    - **memories_used**: how many Cognee memories were retrieved.
    - **memory_trace**: full metadata for each retrieved memory (useful for
      judges to verify the answer came from Cognee, not the base LLM).
    """
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