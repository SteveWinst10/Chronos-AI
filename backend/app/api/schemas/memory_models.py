from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, StrictInt


class MemoryCreate(BaseModel):
    text: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    context: Optional[list[dict[str, Any]]] = None


class MemoryQuery(BaseModel):
    search_query: str = Field(..., min_length=1)
    confidence_threshold: StrictInt = Field(default=70, ge=0, le=100)
    limit: StrictInt = Field(default=10, ge=1, le=100)


class MemoryPurgeRequest(BaseModel):
    target_keys: list[str] = Field(default_factory=list)
    before_timestamp: Optional[datetime] = None
