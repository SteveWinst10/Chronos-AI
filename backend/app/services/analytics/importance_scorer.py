"""
ImportanceScorer: Programmatically calculates importance of events.
Factors: volume, graph centrality, and relationship strength.
"""
from __future__ import annotations

import logging
from typing import Any

from app.api.schemas.story_models import StoryEvent
from app.storage.neo4j_graph import neo4j_graph

logger = logging.getLogger(__name__)


class ImportanceScorer:
    """Calculates importance scores for news events."""

    @staticmethod
    def score_events(events: list[StoryEvent]) -> list[StoryEvent]:
        """
        Computes importance for each event.
        Scores are normalized to 0.0 - 5.0 (star-like rating).
        """
        if not events:
            return []

        scored_events = []
        for event in events:
            # 1. Volume Factor (Number of memories)
            volume_score = min(len(event.memories) / 5.0, 1.0) # Cap at 5 memories
            
            # 2. Graph Centrality Factor
            centrality_sum = 0
            for entity in event.participating_entities:
                degree = neo4j_graph.entity_degree(entity)
                centrality_sum += min(degree / 20.0, 1.0) # Cap each entity at degree 20
            
            avg_centrality = centrality_sum / len(event.participating_entities) if event.participating_entities else 0.5
            
            # 3. Recency Factor (Simulated here, or could use current date)
            # Recent events might be more 'important' in news context.
            
            # Aggregate Score (0.0 - 1.0)
            raw_score = (volume_score * 0.4) + (avg_centrality * 0.6)
            
            # Normalize to 5-star scale
            event.importance = round(raw_score * 5.0, 1)
            scored_events.append(event)

        logger.info(f"Scored {len(scored_events)} events by importance.")
        return scored_events
