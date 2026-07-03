# api/endpoints/news.py
from app.api.schemas.news_models import NewsResponseModel
from fastapi import APIRouter, HTTPException, Query
from app.services.news.news_pipeline import get_cleaned_news_stream
router = APIRouter()

@router.get("/")
async def get_news_by_category(
    category: str = Query(default="technology", description="Category of news to fetch")
):
    try:
        target_category = category.lower().strip()
        
        # 1. Fetch raw cleaned articles stream
        cleaned_data = get_cleaned_news_stream(category=target_category)
        
        # 2. Limit the list to a maximum of 20 items
        limited_data = cleaned_data[:20]
        
        # 3. Restructure into a numbered dictionary starting from 1 instead of 0
        numbered_articles = {}
        for index, article in enumerate(limited_data, start=1):
            numbered_articles[str(index)] = article

        return {
            "status": "success",
            "requested_category": target_category.capitalize(),
            "count": len(limited_data),
            "articles": numbered_articles  # Returns the 1-to-20 dictionary structure
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
