"""Tests for the news pipeline and deduplicator."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from app.services.news.news_pipeline import (
    preprocess_article,
    get_cleaned_news_stream,
    NewsIntelligencePipeline,
)
from app.services.news.deduplicator import Deduplicator, _normalize_text


# ── preprocess_article ────────────────────────────────────────────────────────

def test_preprocess_article_basic():
    raw = {
        "title": "  AI takes over the world!  ",
        "description": "An interesting development.",
        "publishedAt": "2026-06-30T00:35:00Z",
        "source": {"name": "TechNews"},
        "url": "https://example.com/article",
    }
    result = preprocess_article(raw, "technology")
    assert result["title"] == "AI takes over the world!"
    assert result["category"] == "Technology"
    assert result["date"] == "2026-06-30 00:35"
    assert result["source"] == "TechNews"


def test_preprocess_article_missing_description():
    raw = {
        "title": "Breaking News",
        "description": None,
        "publishedAt": "2026-06-30T12:00:00Z",
        "source": {"name": "Reuters"},
        "url": "https://example.com/breaking",
    }
    result = preprocess_article(raw)
    assert result["description"] == "No description available."


def test_preprocess_article_bad_date():
    raw = {
        "title": "Some Story",
        "description": "desc",
        "publishedAt": "not-a-date",
        "source": {"name": "CNN"},
        "url": "https://example.com",
    }
    result = preprocess_article(raw)
    assert result["date"] == "not-a-date"  # falls back to raw string


# ── get_cleaned_news_stream (dedup) ───────────────────────────────────────────

def test_get_cleaned_news_stream_deduplication():
    """Duplicate titles should only appear once in the output."""
    from unittest.mock import patch

    mock_articles = [
        {"title": "Big Story", "description": "desc", "publishedAt": "2026-07-01T00:00:00Z",
         "source": {"name": "BBC"}, "url": "https://bbc.com/1"},
        {"title": "Big Story", "description": "desc2", "publishedAt": "2026-07-01T01:00:00Z",
         "source": {"name": "CNN"}, "url": "https://cnn.com/1"},
    ]

    with patch("app.services.news.news_pipeline.fetch_raw_news", return_value=mock_articles):
        result = get_cleaned_news_stream("technology")

    titles = [a["title"] for a in result]
    assert titles.count("Big Story") == 1


# ── NewsIntelligencePipeline ──────────────────────────────────────────────────

def test_news_intelligence_pipeline_init():
    pipe = NewsIntelligencePipeline(category="sports")
    assert pipe.category == "sports"


# ── Deduplicator ──────────────────────────────────────────────────────────────

def test_normalize_text():
    assert _normalize_text("Hello, World!") == "hello world"
    assert _normalize_text("  Multiple   Spaces  ") == "multiple spaces"


@pytest.mark.asyncio
async def test_deduplicator_first_seen_is_not_duplicate():
    dedup = Deduplicator()
    result = await dedup.is_duplicate("completely unique text xyz 123")
    assert result is False


@pytest.mark.asyncio
async def test_deduplicator_second_occurrence_is_duplicate():
    dedup = Deduplicator()
    text = "the quick brown fox jumps over the lazy dog"
    await dedup.store(text)
    result = await dedup.is_duplicate(text)
    assert result is True
