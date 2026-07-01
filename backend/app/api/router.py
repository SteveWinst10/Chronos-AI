# api/router.py
from fastapi import APIRouter
from api.endpoints.news import router as news_router

api_router = APIRouter(prefix="/api")

# Includes your news endpoint under /api
api_router.include_router(news_router, tags=["News"])