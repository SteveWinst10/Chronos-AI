from __future__ import annotations

import logging
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from app.services.analytics.story_builder import StoryBuilder

router = APIRouter(prefix="/stories", tags=["Stories"])
logger = logging.getLogger(__name__)

class StoryRequest(BaseModel):
    topic: str

@router.post("")
@router.post("/")
async def create_story(request: StoryRequest):
    """Generate a structured multi-stage narrative for a news topic."""
    try:
        story = await StoryBuilder.build_story(request.topic)
        return story
    except Exception as e:
        logger.exception("Story builder failed for %s", request.topic)
        raise HTTPException(status_code=500, detail=str(e))
