"""
EventClustering: Groups memories into distinct real-world events.
Uses entity overlap, temporal proximity, and headline similarity.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Sequence

from app.api.schemas.story_models import StoryEvent, SupportingMemory
from app.services.cognee.recall import MemoryItem

logger = logging.getLogger(__name__)


class EventClustering:
    """Groups retrieved news memories into logical events."""

    @staticmethod
    def cluster_memories(memories: Sequence[MemoryItem]) -> list[StoryEvent]:
        """
        Groups memories that refer to the same event.
        Logic:
        1. Sort memories by date.
        2. Iterate and group if (simliar entities AND date within 3 days) OR (similar title).
        """
        if not memories:
            return []

        # 1. Normalize and Sort
        # Sort by date (descending for easier clustering of recent events)
        sorted_m = sorted(memories, key=lambda x: x.metadata.get("ingested_at", ""), reverse=True)
        
        clusters: list[list[MemoryItem]] = []
        
        for memory in sorted_m:
            placed = False
            for cluster in clusters:
                if EventClustering._is_same_event(memory, cluster[0]):
                    cluster.append(memory)
                    placed = True
                    break
            if not placed:
                clusters.append([memory])

        # 2. Convert clusters to StoryEvent objects
        events = []
        for cluster in clusters:
            primary = cluster[0]
            
            # Extract entities from all memories in cluster
            entities = set()
            for m in cluster:
                # Assuming Cognee or our parser adds entities to metadata
                m_entities = m.metadata.get("entities", [])
                entities.update(m_entities)

            # Support memories
            supporting = [
                SupportingMemory(
                    title=m.title,
                    source=m.source,
                    url=m.link,
                    date=m.metadata.get("ingested_at")
                ) for m in cluster
            ]

            events.append(
                StoryEvent(
                    id=str(uuid.uuid4()),
                    title=primary.title, # LLM can refine this later if needed
                    description=None,
                    participating_entities=list(entities),
                    memories=supporting,
                    start_date=min([m.metadata.get("ingested_at", primary.metadata.get("ingested_at", "")) for m in cluster]),
                    end_date=max([m.metadata.get("ingested_at", primary.metadata.get("ingested_at", "")) for m in cluster]),
                    confidence=sum([m.score for m in cluster]) / len(cluster) if cluster else 0.5
                )
            )

        logger.info(f"Clustered {len(memories)} memories into {len(events)} events.")
        return events

    @staticmethod
    def _is_same_event(m1: MemoryItem, m2: MemoryItem) -> bool:
        """Heuristic to determine if two memories refer to the same event."""
        # 1. Title Similarity (Simple overlap)
        t1 = set(m1.title.lower().split())
        t2 = set(m2.title.lower().split())
        overlap = len(t1.intersection(t2)) / max(len(t1), len(t2))
        if overlap > 0.6:
            return True

        # 2. Entity + Temporal Proximity
        e1 = set(m1.metadata.get("entities", []))
        e2 = set(m2.metadata.get("entities", []))
        
        date1_str = m1.metadata.get("ingested_at")
        date2_str = m2.metadata.get("ingested_at")
        
        if date1_str and date2_str:
            try:
                date1 = datetime.fromisoformat(date1_str.replace("Z", "+00:00"))
                date2 = datetime.fromisoformat(date2_str.replace("Z", "+00:00"))
                if abs((date1 - date2).days) <= 3:
                    # Same entities within 3 days
                    if e1 and e2 and len(e1.intersection(e2)) >= 1:
                        return True
            except Exception:
                pass

        return False
