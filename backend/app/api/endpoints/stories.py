from __future__ import annotations

import logging
import time
from fastapi import APIRouter, HTTPException, Query

from app.api.schemas.story_models import (
    StoryRequest,
    StoryResponse,
    StoryComparisonRequest,
    StoryComparisonResponse
)
from app.services.analytics.story_engine import StoryEvolutionEngine

router = APIRouter(prefix="/stories", tags=["Story Evolution"])
logger = logging.getLogger(__name__)


@router.post("", response_model=StoryResponse)
@router.post("/", response_model=StoryResponse)
async def create_story(request: StoryRequest):
    """
    [PHASE 4] Generates a multi-stage Story Evolution for a topic.
    Workflow: Recall -> Cluster -> Score -> Chapterize -> Summarize.
    """
    start_time = time.time()
    try:
        story = await StoryEvolutionEngine.generate_story(request.topic, debug=request.debug)
        
        logger.info(
            "POST /stories — Topic: %s — Confidence: %s — ExecTime: %.2fms",
            request.topic, story.confidence, (time.time() - start_time) * 1000
        )
        
        return story
    except Exception as e:
        logger.exception("Story Evolution failed for %s", request.topic)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare", response_model=StoryComparisonResponse)
async def compare_stories(request: StoryComparisonRequest):
    """
    [PHASE 4] Compares two news topics by generating parallel timelines and identifying overlaps.
    """
    start_time = time.time()
    try:
        comparison = await StoryEvolutionEngine.compare_stories(
            request.topic_a, 
            request.topic_b, 
            debug=request.debug
        )
        
        logger.info(
            "POST /stories/compare — %s vs %s — ExecTime: %.2fms",
            request.topic_a, request.topic_b, (time.time() - start_time) * 1000
        )
        
        return comparison
    except Exception as e:
        logger.exception("Story Comparison failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{topic}", response_model=StoryResponse)
async def get_story_by_topic(topic: str, debug: bool = Query(False)):
    """Convenience GET endpoint for story generation."""
    return await create_story(StoryRequest(topic=topic, debug=debug))


@router.get("/{topic}/timeline")
async def get_story_timeline(topic: str):
    """Returns only the chronological event timeline for a topic."""
    story = await StoryEvolutionEngine.generate_story(topic)
    return {
        "topic": topic,
        "timeline": story.timeline
    }


@router.get("/{topic}/chapters")
async def get_story_chapters(topic: str):
    """Returns only the synthesized chapters for a topic story."""
    story = await StoryEvolutionEngine.generate_story(topic)
    return {
        "topic": topic,
        "chapters": [{ "title": c.title, "summary": c.summary } for c in story.chapters]
    }
