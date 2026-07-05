"""
Lifecycle Tracker — Final Phase

A singleton in-memory event log that records every major memory operation
(remember, recall, improve, forget, story generation) with timestamps,
duration, affected entities, and status. Serves as the system's audit trail.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class EventType(str, Enum):
    INGESTION = "ingestion"
    RECALL = "recall"
    IMPROVEMENT = "improvement"
    STORY_GENERATION = "story_generation"
    FORGET = "forget"
    SYSTEM = "system"


@dataclass
class LifecycleEvent:
    event_type: EventType
    description: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    duration_ms: Optional[float] = None
    affected_entities: list[str] = field(default_factory=list)
    affected_memories: int = 0
    status: str = "success"  # "success" | "failed" | "partial"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "affected_entities": self.affected_entities,
            "affected_memories": self.affected_memories,
            "status": self.status,
            "metadata": self.metadata,
        }


class LifecycleTracker:
    """Singleton that maintains the complete memory lifecycle event log."""

    _events: list[LifecycleEvent] = []
    _start_time: float = time.time()
    _last_ingestion: Optional[datetime] = None
    _last_improvement: Optional[datetime] = None
    _total_ingested: int = 0
    _total_recalls: int = 0
    _total_improvements: int = 0
    _total_forgets: int = 0

    @classmethod
    def log(
        cls,
        event_type: EventType,
        description: str,
        *,
        duration_ms: Optional[float] = None,
        affected_entities: Optional[list[str]] = None,
        affected_memories: int = 0,
        status: str = "success",
        metadata: Optional[dict] = None,
    ) -> LifecycleEvent:
        event = LifecycleEvent(
            event_type=event_type,
            description=description,
            duration_ms=duration_ms,
            affected_entities=affected_entities or [],
            affected_memories=affected_memories,
            status=status,
            metadata=metadata or {},
        )
        cls._events.append(event)

        # Update counters
        if event_type == EventType.INGESTION:
            cls._total_ingested += affected_memories
            cls._last_ingestion = event.timestamp
        elif event_type == EventType.IMPROVEMENT:
            cls._total_improvements += 1
            cls._last_improvement = event.timestamp
        elif event_type == EventType.RECALL:
            cls._total_recalls += 1
        elif event_type == EventType.FORGET:
            cls._total_forgets += 1

        return event

    @classmethod
    def get_timeline(cls, limit: int = 50, event_type: Optional[EventType] = None) -> list[dict]:
        events = cls._events
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return [e.to_dict() for e in reversed(events[-limit:])]

    @classmethod
    def get_stats(cls) -> dict[str, Any]:
        return {
            "uptime_seconds": round(time.time() - cls._start_time, 1),
            "total_ingested": cls._total_ingested,
            "total_recalls": cls._total_recalls,
            "total_improvements": cls._total_improvements,
            "total_forgets": cls._total_forgets,
            "last_ingestion": cls._last_ingestion.isoformat() if cls._last_ingestion else None,
            "last_improvement": cls._last_improvement.isoformat() if cls._last_improvement else None,
            "total_events": len(cls._events),
        }
