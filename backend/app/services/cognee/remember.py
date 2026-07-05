"""Article ingestion helpers for Cognee memory.

This module starts after the news pipeline has already fetched and parsed an
article. It validates the article, formats it as a stable memory document, and
stores it in Cognee's permanent `news` dataset.
"""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Mapping, TypedDict

logger = logging.getLogger(__name__)

NEWS_DATASET = "news"
REQUIRED_ARTICLE_FIELDS = ("title", "content", "source", "link")


class ArticleValidationError(ValueError):
    """Raised when an incoming article is missing required usable data."""


class ArticleStorageError(RuntimeError):
    """Raised when Cognee cannot store a validated article document."""


class RememberArticleResult(TypedDict, total=False):
    """Structured result returned by article memory ingestion."""

    success: bool
    message: str
    source: str
    title: str
    timestamp: str
    dataset: str
    error: str


@dataclass(frozen=True)
class MemoryDocument:
    """Formatted article document plus metadata used for ingestion."""

    text: str
    title: str
    source: str
    link: str
    ingested_at: str
    dataset: str = NEWS_DATASET


def validate_article(article: Mapping[str, Any]) -> None:
    """Validate that an article contains the required non-empty fields.

    Args:
        article: Parsed article mapping from the existing news pipeline.

    Raises:
        ArticleValidationError: If the article is not a mapping, is missing
            required fields, or contains blank values.
    """

    if not isinstance(article, Mapping):
        raise ArticleValidationError("Article must be a mapping/dictionary.")

    missing_fields = [field for field in REQUIRED_ARTICLE_FIELDS if field not in article]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ArticleValidationError(f"Article is missing required field(s): {missing}.")

    empty_fields = [
        field
        for field in REQUIRED_ARTICLE_FIELDS
        if not str(article.get(field, "")).strip()
    ]
    if empty_fields:
        empty = ", ".join(empty_fields)
        raise ArticleValidationError(f"Article field(s) cannot be empty: {empty}.")


def build_memory_document(article: Mapping[str, Any]) -> MemoryDocument:
    """Build a structured Cognee memory document from a validated article.

    Args:
        article: Parsed and validated article mapping.

    Returns:
        A formatted memory document and internal metadata.
    """

    title = str(article["title"]).strip()
    source = str(article["source"]).strip()
    link = str(article["link"]).strip()
    content = str(article["content"]).strip()
    ingested_at = datetime.now(UTC).isoformat()

    document = (
        "Title:\n"
        f"{title}\n\n"
        "Source:\n"
        f"{source}\n\n"
        "Link:\n"
        f"{link}\n\n"
        "Content:\n"
        f"{content}\n"
    )

    return MemoryDocument(
        text=document,
        title=title,
        source=source,
        link=link,
        ingested_at=ingested_at,
    )


async def store_article(memory_document: MemoryDocument) -> Any:
    """Store a formatted article document in Cognee.

    The installed Cognee SDK exposes `async cognee.remember(data,
    dataset_name=..., session_id=None, ...)`. Omitting `session_id` stores
    permanent graph memory.

    Args:
        memory_document: Structured article document to store.

    Returns:
        The raw Cognee SDK result.

    Raises:
        ArticleStorageError: If Cognee is unavailable or rejects the document.
    """

    try:
        import cognee
    except ImportError as exc:
        raise ArticleStorageError("Cognee SDK is not installed.") from exc

    remember = getattr(cognee, "remember", None)
    if remember is None:
        raise ArticleStorageError("Cognee SDK does not expose a remember() API.")

    try:
        result = remember(
            memory_document.text,
            dataset_name=memory_document.dataset,
            run_in_background=False,
        )
        if inspect.isawaitable(result):
            result = await result
        return result
    except Exception as exc:
        logger.exception(
            "Cognee failed to store article.",
            extra={
                "title": memory_document.title,
                "source": memory_document.source,
                "dataset": memory_document.dataset,
            },
        )
        raise ArticleStorageError(f"Cognee failed to store article: {exc}") from exc


def _success_result(memory_document: MemoryDocument) -> RememberArticleResult:
    return {
        "success": True,
        "message": "Article stored successfully",
        "source": memory_document.source,
        "title": memory_document.title,
        "timestamp": memory_document.ingested_at,
        "dataset": memory_document.dataset,
    }


def _failure_result(
    message: str,
    *,
    article: Mapping[str, Any] | None = None,
    timestamp: str | None = None,
) -> RememberArticleResult:
    safe_article = article if isinstance(article, Mapping) else {}
    return {
        "success": False,
        "message": message,
        "source": str(safe_article.get("source", "")).strip(),
        "title": str(safe_article.get("title", "")).strip(),
        "timestamp": timestamp or datetime.now(UTC).isoformat(),
        "dataset": NEWS_DATASET,
        "error": message,
    }


async def remember_article(article: Mapping[str, Any]) -> RememberArticleResult:
    """Validate, transform, and store one parsed news article in Cognee.

    Args:
        article: Parsed article with `title`, `content`, `source`, and `link`.

    Returns:
        A structured success or failure result for the ingestion attempt.
    """

    memory_document: MemoryDocument | None = None

    try:
        validate_article(article)
        memory_document = build_memory_document(article)
        await store_article(memory_document)
        logger.info(
            "Article stored in Cognee.",
            extra={
                "title": memory_document.title,
                "source": memory_document.source,
                "dataset": memory_document.dataset,
            },
        )
        return _success_result(memory_document)
    except ArticleValidationError as exc:
        logger.warning("Article validation failed: %s", exc)
        return _failure_result(str(exc), article=article)
    except ArticleStorageError as exc:
        logger.error("Article storage failed: %s", exc)
        return _failure_result(
            str(exc),
            article=article,
            timestamp=memory_document.ingested_at if memory_document else None,
        )
    except Exception as exc:
        logger.exception("Unexpected article ingestion failure.")
        return _failure_result(
            f"Unexpected article ingestion failure: {exc}",
            article=article,
            timestamp=memory_document.ingested_at if memory_document else None,
        )
