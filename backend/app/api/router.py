from fastapi import APIRouter
from app.api.endpoints.news import router as news_router
# from app.api.endpoints.chat import router as chat_router (etc.)

api_router = APIRouter(prefix="/api")
api_router.include_router(news_router, tags=["News"])