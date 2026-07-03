    # app/api/schemas/news_models.py
from pydantic import BaseModel, Field
from typing import Dict
from typing import Dict

from pydantic import BaseModel, Field


class NewsDocumentIngest(BaseModel):
    title: str
    url: str
    content: str
    source: str
    keywords: list[str] = Field(default_factory=list)


class ArticleModel(BaseModel):
    title: str = Field(..., description="The cleaned title of the news article")
    description: str = Field(..., description="The sanitized description summary")
    date: str = Field(..., description="Standardized date timestamp (YYYY-MM-DD HH:MM)")
    source: str = Field(..., description="The publisher or news origin source")
    category: str = Field(..., description="The dynamic category requested")
    url: str = Field(..., description="The direct web URL address")

class NewsResponseModel(BaseModel):
    status: str
    requested_category: str
    count: int
    articles: Dict[str, ArticleModel]  # Matches your custom 1-to-20 indexing

class NewsResponseSchema(BaseModel):
    status: str
    requested_category: str
    count: int
    articles: Dict[str, ArticleSchema]
