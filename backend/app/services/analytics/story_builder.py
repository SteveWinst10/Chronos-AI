"""
StoryBuilder: generates structured narratives (stories) from news trajectories.
Transforms a set of chronological facts into a multi-stage story.
"""
from __future__ import annotations

import logging
from datetime import datetime, UTC
from typing import Any

from app.services.analytics.timeline import TimelineBuilder
from app.services.llm.llm_client import LLMClient

logger = logging.getLogger(__name__)


class StoryBuilder:
    """Service to synthesize structured narratives from retrieved news memories."""

    @staticmethod
    async def build_story(topic: str) -> dict[str, Any]:
        """
        [PHASE 3] Assembles a structured narrative from retrieved memories.
        Stages: Beginning -> Major Announcement -> Adoption -> Recent -> Status.
        """
        logger.info(f"Generating story for: {topic}")

        # 1. Get chronological timeline data
        timeline = await TimelineBuilder.build_timeline(topic, limit=15)
        
        if not timeline:
            return {
                "title": f"The Story of {topic}",
                "summary": "No enough information found to construct a story.",
                "stages": []
            }

        # 2. Prepare context for LLM to structure the story
        facts = "\n".join([
            f"[{e['date']}] {e['title']}: {e['summary']}" 
            for e in timeline
        ])

        system_prompt = (
            "You are a Senior News Analyst. Your task is to take a chronological list of news events "
            "and transform them into a structured narrative called a 'Story'.\n\n"
            "The story must have the following stages:\n"
            "1. Beginning (Origin/Context)\n"
            "2. Major Announcement (The pivot point)\n"
            "3. Adoption/Impact (How it went into the world)\n"
            "4. Recent Developments\n"
            "5. Current Status\n\n"
            "Summarize each stage based ONLY on the provided news events. "
            "If information for a stage is missing, say 'Information not available'."
        )

        user_prompt = f"Topic: {topic}\n\nChronological Events:\n{facts}\n\nGenerate the structured story."

        llm = LLMClient()
        try:
            # We'll use a specific format for the LLM to follow or just parse it
            story_text = await llm.get_completion(user_prompt, system_prompt)
        except Exception as e:
            logger.error(f"Story synthesis failed: {e}")
            story_text = "Failed to synthesize narrative."

        return {
            "title": f"The Evolution of {topic}",
            "topic": topic,
            "timeline": timeline,
            "narrative": story_text,
            "metadata": {
                "event_count": len(timeline),
                "generated_at": datetime.now(UTC).isoformat()
            }
        }
