from typing import Any, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: Optional[str] = None


class ChatResponseChunk(BaseModel):
    token_text: str
    is_final: bool = False
    source_nodes: Optional[list[dict[str, Any]]] = None
