# app/api/schemas/news_models.py
from pydantic import BaseModel
from typing import List, Dict

class ArticleSchema(BaseModel):
    title: str
    description: str
    date: str
    source: str
    category: str
    url: str

class NewsResponseSchema(BaseModel):
    status: str
    requested_category: str
    count: int
    articles: Dict[str, ArticleSchema] # Matches your 1-to-20 custom numbering system!