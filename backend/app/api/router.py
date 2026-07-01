from fastapi import APIRouter

# Import endpoint routers
from app.api.endpoints.news import router as news_router
from app.api.endpoints.health import router as health_router
# Placeholder imports for other routers
from app.api.endpoints.chat import router as chat_router
from app.api.endpoints.graph import router as graph_router
from app.api.endpoints.memory import router as memory_router
from app.api.endpoints.stories import router as stories_router
from app.api.endpoints.timeline import router as timeline_router

api_router = APIRouter()

# Include routers under versioned prefix
api_router.include_router(news_router, prefix="/v1/news", tags=["News"])
api_router.include_router(health_router, prefix="/v1", tags=["Health"])
# Uncomment and include other routers when implemented
api_router.include_router(chat_router, prefix="/v1/chat", tags=["Chat"])
api_router.include_router(graph_router, prefix="/v1/graph", tags=["Graph"])
api_router.include_router(memory_router, prefix="/v1/memory", tags=["Memory"])
api_router.include_router(stories_router, prefix="/v1/stories", tags=["Stories"])
api_router.include_router(timeline_router, prefix="/v1/timeline", tags=["Timeline"])