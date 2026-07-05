"""
TimelineBuilder: constructs chronological event sequences for entities or topics.
Connects graph entities back to their source articles stored in Cognee.
"""
from __future__ import annotations

import logging
from datetime import datetime, UTC
from typing import Any

from app.services.cognee.recall import recall_memories, MemoryItem

logger = logging.getLogger(__name__)


class TimelineBuilder:
    """Service to generate chronological timelines for news topics."""

    @staticmethod
    async def build_timeline(topic: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        [PHASE 3] Creates a chronological timeline for a given topic/entity.
        Workflow:
        1. Recall memories (articles) from Cognee related to the topic.
        2. Parse temporal metadata from memories.
        3. Sort by date and format as timeline events.
        """
        logger.info(f"Building timeline for: {topic}")
        
        # In a pure graph approach, we would query: (Entity)-[:MENTIONED_IN]-(Article)
        # But for high accuracy during the hackathon, we combine recall with metadata sorting.
        memories = await recall_memories(topic, limit=limit)
        
        if not memories:
            logger.info(f"No memories found to build a timeline for {topic}.")
            return []

        events = []
        for memory in memories:
            # Attempt to extract date from metadata if Cognee provided it, 
            # otherwise use current time or a placeholder.
            date_str = memory.metadata.get("ingested_at") or memory.metadata.get("date")
            
            # Simple date parsing logic
            try:
                if date_str:
                    event_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                else:
                    event_date = datetime.now()
            except Exception:
                event_date = datetime.now()

            events.append({
                "title": memory.title,
                "date": event_date.strftime("%b %d, %Y"),
                "iso_date": event_date.isoformat(),
                "source": memory.source,
                "link": memory.link,
                "summary": memory.content[:300] + "..." if len(memory.content) > 300 else memory.content,
                "relevance": memory.score
            })

        # Sort chronologically (oldest to newest) or newest first?
        # Typically timelines are chronological (old to new), but news users often want new to old.
        # We'll stick to chronological (ASC) for a 'story' feel.
        events.sort(key=lambda x: x["iso_date"])
        
        logger.info(f"Timeline built with {len(events)} events for {topic}.")
        return events
