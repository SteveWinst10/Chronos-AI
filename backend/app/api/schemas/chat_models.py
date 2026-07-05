# app/api/schemas/chat_models.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the message sender: 'user' or 'assistant'")
    content: str = Field(..., description="The text content of the message")


class ChatRequest(BaseModel):
    message: str = Field(..., description="The prompt or question sent to the assistant")
    history: Optional[List[ChatMessage]] = Field(
        default=[], description="Previous conversational history log"
    )


class MemoryTraceItem(BaseModel):
    """One retrieved memory included in the LLM context — exposed for judges."""

    rank: int = Field(..., description="Relevance rank (1 = most relevant)")
    title: str = Field(default="", description="Article headline")
    source: str = Field(default="", description="Publisher / origin")
    link: str = Field(default="", description="Canonical article URL")
    relevance_score: float = Field(default=0.0, description="Cognee relevance score (0.0 if unavailable)")
    content_preview: str = Field(default="", description="First 200 characters of the article body")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extra Cognee metadata")


class SourceItem(BaseModel):
    """Deduplicated source reference for the answer."""

    title: str = Field(default="", description="Article title")
    source: str = Field(default="", description="Publisher / origin")
    link: str = Field(default="", description="Article URL")


class ChatResponse(BaseModel):
    status: str
    response: str = Field(..., description="The generated response from the assistant agent")
    sources: List[SourceItem] = Field(
        default_factory=list,
        description="Deduplicated list of cited sources used to generate the answer",
    )
    memories_used: int = Field(
        default=0,
        description="Number of Cognee memories retrieved and included in the LLM context",
    )
    memory_trace: List[MemoryTraceItem] = Field(
        default_factory=list,
        description=(
            "Detailed trace of every memory retrieved from Cognee. "
            "Demonstrates that the answer is grounded in persistent memory, "
            "not the base LLM's pretrained knowledge."
        ),
    )