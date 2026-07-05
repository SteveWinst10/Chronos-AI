from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SupportingMemory(BaseModel):
    title: str
    source: str
    url: str
    date: Optional[str] = None


class StoryEvent(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    participating_entities: list[str] = Field(default_factory=list)
    memories: list[SupportingMemory] = Field(default_factory=list)
    start_date: str
    end_date: Optional[str] = None
    importance: float = 0.0
    confidence: float = 1.0


class StoryChapter(BaseModel):
    title: str
    summary: str
    events: list[StoryEvent] = Field(default_factory=list)
    sources: list[SupportingMemory] = Field(default_factory=list)


class StoryStatistics(BaseModel):
    memories_used: int
    events_detected: int
    chapters_generated: int
    entities_connected: int


class StoryResponse(BaseModel):
    title: str
    topic: str
    confidence: float
    chapters: list[StoryChapter] = Field(default_factory=list)
    timeline: list[StoryEvent] = Field(default_factory=list)
    related_entities: list[str] = Field(default_factory=list)
    key_events: list[str] = Field(default_factory=list)
    statistics: StoryStatistics
    debug_artifacts: Optional[dict[str, Any]] = None


class StoryComparisonResponse(BaseModel):
    topic_a: StoryResponse
    topic_b: StoryResponse
    shared_entities: list[str] = Field(default_factory=list)
    common_events: list[str] = Field(default_factory=list)
    unique_events_a: list[str] = Field(default_factory=list)
    unique_events_b: list[str] = Field(default_factory=list)
    summary_comparison: str


class StoryRequest(BaseModel):
    topic: str
    debug: bool = False


class StoryComparisonRequest(BaseModel):
    topic_a: str
    topic_b: str
    debug: bool = False
