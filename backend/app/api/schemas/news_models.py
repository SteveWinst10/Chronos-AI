from typing import Dict

from pydantic import BaseModel, Field


class NewsDocumentIngest(BaseModel):
    title: str
    url: str
    content: str
    source: str
    keywords: list[str] = Field(default_factory=list)


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
    articles: Dict[str, ArticleSchema]
