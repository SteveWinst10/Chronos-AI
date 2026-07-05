"""
StoryEvolutionEngine: The main orchestrator for Phase 4.
Reconstructs topic evolution using clustered events, importance, and chaptering.
"""
from __future__ import annotations

import logging
from datetime import datetime, UTC
from typing import Any, Sequence

from app.api.schemas.story_models import (
    StoryChapter,
    StoryEvent,
    StoryResponse,
    StoryStatistics,
    SupportingMemory,
)
from app.services.analytics.event_clustering import EventClustering
from app.services.analytics.importance_scorer import ImportanceScorer
from app.services.cognee.recall import recall_memories, MemoryItem
from app.services.llm.llm_client import LLMClient
from app.storage.neo4j_graph import neo4j_graph

logger = logging.getLogger(__name__)

# Simple in-memory cache for generated stories
_story_cache: dict[str, StoryResponse] = {}

class StoryEvolutionEngine:
    """Orchestrates the multi-stage News Intelligence Story Engine."""

    @staticmethod
    async def generate_story(topic: str, debug: bool = False, use_cache: bool = True) -> StoryResponse:
        """
        [PHASE 4] Reconstructs the story of a topic from Cognee memories.
        """
        if use_cache and not debug and topic in _story_cache:
            logger.info(f"Returning cached story for topic: {topic}")
            return _story_cache[topic]

        logger.info(f"Generating Story Evolution for: {topic}")
        debug_artifacts = {} if debug else None

        # Step 1: Recall Memories
        memories = await recall_memories(topic, limit=25)
        if debug:
            debug_artifacts["retrieved_memories_count"] = len(memories)

        if not memories:
            logger.info(f"No memories found for {topic}. Returning empty story.")
            return StoryEvolutionEngine._empty_response(topic, debug_artifacts)

        # Step 2: Event Clustering (Programmatic)
        events = EventClustering.cluster_memories(memories)
        if debug:
            debug_artifacts["events_detected"] = len(events)

        # Step 3: Event Importance (Programmatic)
        scored_events = ImportanceScorer.score_events(events)

        # Step 4: Timeline Construction (Deterministic)
        # Sort events by start date ascending
        timeline = sorted(scored_events, key=lambda x: x.start_date)

        # Step 5: Chapter Generation (Rules-based)
        chapters = StoryEvolutionEngine._generate_chapters_structure(timeline)
        if debug:
            debug_artifacts["chapters_generated"] = len(chapters)

        # Step 6: Narrative Generation (Grounded LLM)
        full_chapters = await StoryEvolutionEngine._generate_narratives(topic, chapters)

        # Step 7: Story Confidence Calculation
        avg_event_conf = sum(e.confidence for e in timeline) / len(timeline) if timeline else 0.5
        overall_confidence = round(avg_event_conf * 0.95, 2) # Slightly penalize for gaps

        # Collect Analytics
        entities = set()
        for e in timeline:
            entities.update(e.participating_entities)

        stats = StoryStatistics(
            memories_used=len(memories),
            events_detected=len(timeline),
            chapters_generated=len(full_chapters),
            entities_connected=len(entities)
        )

        result = StoryResponse(
            title=f"The Evolution of {topic}",
            topic=topic,
            confidence=overall_confidence,
            chapters=full_chapters,
            timeline=timeline,
            related_entities=list(entities)[:10],
            key_events=[e.title for e in timeline if e.importance >= 4.0],
            statistics=stats,
            debug_artifacts=debug_artifacts
        )

        if not debug:
            _story_cache[topic] = result

        return result

    @staticmethod
    def _generate_chapters_structure(timeline: list[StoryEvent]) -> list[StoryChapter]:
        """
        Groups events into logical chapters based on timeline density and count.
        """
        if not timeline:
            return []

        # Simple grouping: 2-3 events per chapter
        chapter_list = []
        chunk_size = 3
        for i in range(0, len(timeline), chunk_size):
            chunk = timeline[i:i + chunk_size]
            title = f"Phase {len(chapter_list) + 1}: {chunk[0].title}"
            
            # Aggregate sources
            sources = []
            for e in chunk:
                sources.extend(e.memories)

            chapter_list.append(
                StoryChapter(
                    title=title,
                    summary="...", # To be filled by LLM
                    events=chunk,
                    sources=sources
                )
            )
        return chapter_list

    @staticmethod
    async def _generate_narratives(topic: str, chapters: list[StoryChapter]) -> list[StoryChapter]:
        """Uses LLM to summarize each chapter based ONLY on provided events."""
        llm = LLMClient()
        
        for chapter in chapters:
            evidence = "\n".join([
                f"- Event: {e.title} ({e.start_date}) Description: {e.description or 'No desc'}. "
                f"Source Examples: {', '.join([m.title for m in e.memories[:2]])}"
                for e in chapter.events
            ])

            prompt = (
                f"Synthesize a concise summary for Chapter '{chapter.title}' of the topic '{topic}'.\n\n"
                f"Evidence from Cognee Memory:\n{evidence}\n\n"
                "Rules:\n"
                "1. Strictly use ONLY the evidence above.\n"
                "2. Maintain chronological order.\n"
                "3. Cite at least one primary source title if applicable.\n"
            )

            try:
                chapter.summary = await llm.get_completion(prompt, "You are a Story Evolution Analyst.")
            except Exception:
                chapter.summary = "Summary generation failed."
        
        return chapters

    @staticmethod
    async def compare_stories(topic_a: str, topic_b: str, debug: bool = False) -> StoryComparisonResponse:
        """
        [PHASE 4] Compares the stories of two topics.
        """
        from app.api.schemas.story_models import StoryComparisonResponse

        story_a = await StoryEvolutionEngine.generate_story(topic_a, debug)
        story_b = await StoryEvolutionEngine.generate_story(topic_b, debug)

        # Identify Shared Entities
        shared_entities = list(set(story_a.related_entities).intersection(set(story_b.related_entities)))
        
        # Shared events (very simple title check for now)
        common_events = []
        titles_a = {e.title.lower() for e in story_a.timeline}
        titles_b = {e.title.lower() for e in story_b.timeline}
        common_events = list(titles_a.intersection(titles_b))

        unique_a = list(titles_a - titles_b)
        unique_b = list(titles_b - titles_a)

        # Generate comparison summary
        llm = LLMClient()
        comp_prompt = (
            f"Compare the evolution of '{topic_a}' and '{topic_b}'.\n"
            f"Topic A Key Events: {', '.join(story_a.key_events)}\n"
            f"Topic B Key Events: {', '.join(story_b.key_events)}\n"
            f"Shared Entities: {', '.join(shared_entities)}\n\n"
            "Identify key differences and overlaps in their market trajectories."
        )
        
        try:
            summary = await llm.get_completion(comp_prompt, "You are a Competitive Analyst.")
        except Exception:
            summary = "Comparison summary failed."

        return StoryComparisonResponse(
            topic_a=story_a,
            topic_b=story_b,
            shared_entities=shared_entities,
            common_events=common_events,
            unique_events_a=unique_a,
            unique_events_b=unique_b,
            summary_comparison=summary
        )

    @staticmethod
    def _empty_response(topic: str, debug_artifacts: dict | None) -> StoryResponse:
        return StoryResponse(
            title=f"The Evolution of {topic}",
            topic=topic,
            confidence=0.0,
            chapters=[],
            timeline=[],
            statistics=StoryStatistics(0, 0, 0, 0),
            debug_artifacts=debug_artifacts
        )
