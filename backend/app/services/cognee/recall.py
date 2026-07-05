"""Cognee recall wrapper for the Chronos-AI retrieval pipeline.

Sole responsibility: ask Cognee's memory layer for memories relevant to a
query and return them as normalised ``MemoryItem`` objects.
"""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass, field
from typing import Any, Sequence

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class RecallUnavailableError(RuntimeError):
    """Raised when the Cognee SDK is not installed or has no recall() API."""

class RecallExecutionError(RuntimeError):
    """Raised when Cognee's recall() call fails at runtime."""

# ---------------------------------------------------------------------------
# Normalised memory container
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MemoryItem:
    """A single normalised memory retrieved from Cognee."""
    title: str
    content: str
    source: str
    link: str
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_TITLE_MARKERS = ("title:", "Title:")
_SOURCE_MARKERS = ("source:", "Source:")
_LINK_MARKERS = ("link:", "Link:")
_CONTENT_MARKERS = ("content:", "Content:")

def _extract_section(text: str, *markers: str) -> str:
    """Extract one labelled section from a stored Cognee document."""
    lower = text.lower()
    for marker in markers:
        idx = lower.find(marker.lower())
        if idx == -1:
            continue
        # Skip past the marker line
        start = text.find("\n", idx)
        if start == -1:
            continue
        start += 1  # character after the newline

        # Find where the next section begins (blank line before a known label)
        end = len(text)
        for other_marker in (*_TITLE_MARKERS, *_SOURCE_MARKERS, *_LINK_MARKERS, *_CONTENT_MARKERS):
            if other_marker.lower() == marker.lower():
                continue
            other_idx = lower.find(other_marker.lower(), start)
            if other_idx != -1 and other_idx < end:
                # Walk back to the blank line that precedes this section
                newline_before = text.rfind("\n\n", start, other_idx)
                if newline_before != -1:
                    end = newline_before
                else:
                    end = other_idx
        
        return text[start:end].strip()
    return ""

def _normalise_raw_result(raw: Any) -> MemoryItem | None:
    """Convert a single raw Cognee result object to a ``MemoryItem``."""
    payload: str = ""
    score: float = 0.0
    extra: dict[str, Any] = {}

    if isinstance(raw, dict):
        payload = str(raw.get("text") or raw.get("content") or raw.get("payload") or "")
        score = float(raw.get("score") or raw.get("relevance") or 0.0)
        extra = {k: v for k, v in raw.items() if k not in {"text", "content", "payload", "score", "relevance"}}
    elif hasattr(raw, "text"):
        payload = str(getattr(raw, "text", "") or "")
        score = float(getattr(raw, "score", 0.0) or 0.0)
        for attr in ("id", "dataset", "created_at", "chunk_index"):
            val = getattr(raw, attr, None)
            if val is not None:
                extra[attr] = val
    elif isinstance(raw, str):
        payload = raw
    else:
        return None

    if not payload.strip():
        return None

    title = _extract_section(payload, *_TITLE_MARKERS)
    source = _extract_section(payload, *_SOURCE_MARKERS)
    link = _extract_section(payload, *_LINK_MARKERS)
    content = _extract_section(payload, *_CONTENT_MARKERS)

    if not content and not title:
        content = payload.strip()

    return MemoryItem(
        title=title,
        content=content,
        source=source,
        link=link,
        score=score,
        metadata=extra,
    )

async def recall_memories(query: str, limit: int = 8) -> list[MemoryItem]:
    """Retrieve normalised memories from Cognee relevant to *query*."""
    if not query or not query.strip():
        return []

    try:
        import cognee
    except ImportError as exc:
        raise RecallUnavailableError("Cognee SDK is not installed.") from exc

    recall_fn = getattr(cognee, "recall", None)
    if recall_fn is None:
        raise RecallUnavailableError("Cognee SDK does not expose a recall() API.")

    try:
        raw_results = recall_fn(query, top_k=limit)
        if inspect.isawaitable(raw_results):
            raw_results = await raw_results
    except Exception as exc:
        logger.exception("Cognee recall() failed.")
        raise RecallExecutionError(f"Cognee recall failed: {exc}") from exc

    if raw_results is None:
        return []

    if not isinstance(raw_results, (list, tuple, Sequence)) or isinstance(raw_results, (str, bytes)):
        try:
            raw_results = list(raw_results)
        except TypeError:
            return []

    memories: list[MemoryItem] = []
    for idx, raw in enumerate(raw_results):
        item = _normalise_raw_result(raw)
        if item is not None:
            memories.append(item)

    return memories[:limit]
