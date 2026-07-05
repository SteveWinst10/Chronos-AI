"""
TimelineBuilder: constructs chronological event sequences for entities or topics.
Refactored for Phase 4 to use Event Intelligence (Clustering + Scoring).
"""
from __future__ import annotations

import logging
from typing import Any

from app.services.analytics.event_clustering import EventClustering
from app.services.analytics.importance_scorer import ImportanceScorer
from app.services.cognee.recall import recall_memories

logger = logging.getLogger(__name__)


class TimelineBuilder:
    """Service to generate chronological timelines for news topics using Event Intelligence."""

    @staticmethod
    async def build_timeline(topic: str, limit: int = 20) -> list[dict[str, Any]]:
        """
        [PHASE 4] Creates a chronological timeline using clustered events.
        """
        logger.info(f"Building Phase 4 timeline for: {topic}")
        
        # 1. Recall memories
        memories = await recall_memories(topic, limit=limit)
        if not memories:
            return []

        # 2. Cluster into events
        events = EventClustering.cluster_memories(memories)
        
        # 3. Score events
        scored_events = ImportanceScorer.score_events(events)
        
        # 4. Sort and Format
        timeline = sorted(scored_events, key=lambda x: x.start_date)
        
        return [
            {
                "id": e.id,
                "title": e.title,
                "start_date": e.start_date,
                "end_date": e.end_date,
                "importance": e.importance,
                "participating_entities": e.participating_entities,
                "memory_count": len(e.memories),
                "summary": e.description or (e.memories[0].title if e.memories else ""),
                "sources": [m.dict() for m in e.memories]
            }
            for e in timeline
        ]
