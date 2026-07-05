from __future__ import annotations

import logging
import time
from fastapi import APIRouter, HTTPException

from app.services.analytics.timeline import TimelineBuilder

router = APIRouter(prefix="/timeline", tags=["Timeline"])
logger = logging.getLogger(__name__)

@router.get("/{topic}")
async def get_timeline(topic: str):
    """Retrieve a chronological sequence of news events for a topic."""
    start_time = time.time()
    
    try:
        events = await TimelineBuilder.build_timeline(topic)
        
        logger.info(
            "GET /timeline/%s — Events returned: %d — ExecTime: %.2fms",
            topic, len(events), (time.time() - start_time) * 1000
        )
        
        return {
            "topic": topic,
            "event_count": len(events),
            "timeline": events
        }
    except Exception as e:
        logger.exception("Timeline generation failed for %s", topic)
        raise HTTPException(status_code=500, detail=str(e))
