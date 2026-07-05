"""Cognee recall wrapper for the Chronos-AI retrieval pipeline.

Sole responsibility: ask Cognee's memory layer for memories relevant to a
query and return them as normalised ``MemoryItem`` objects.

Rules
-----
- No LLM calls.
- No prompt engineering.
- No business logic beyond normalisation and logging.
- Callable independently; all side-effects are inside Cognee.
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
    """A single normalised memory retrieved from Cognee.

    All fields are strings so callers never have to worry about None checks
    or type coercions before passing data downstream.

    Attributes:
        title:    Article headline extracted from the stored document.
        content:  Body text of the article.
        source:   Publisher / origin of the article (e.g. "BBC News").
        link:     Canonical URL of the original article.
        score:    Relevance score returned by Cognee, 0.0 if unavailable.
        metadata: Any extra key-value pairs forwarded from Cognee verbatim.
    """

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
    """Extract one labelled section from a stored Cognee document.

    The ``remember.py`` module writes articles in the format::

        Title:
        <value>

        Source:
        <value>

        …

    This helper finds the first matching marker and returns everything up to
    the next blank-line-separated section (or end of string).
    """
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
    """Convert a single raw Cognee result object to a ``MemoryItem``.

    Cognee may return different shapes depending on the version installed
    (dataclasses, dicts, objects with attributes). This function handles the
    most common shapes defensively.

    Returns ``None`` when the result cannot be meaningfully normalised.
    """
    # -----------------------------------------------------------------------
    # Extract the plain-text payload and relevance score
    # -----------------------------------------------------------------------
    payload: str = ""
    score: float = 0.0
    extra: dict[str, Any] = {}

    if isinstance(raw, dict):
        # Dict-like result from some Cognee versions
        payload = str(raw.get("text") or raw.get("content") or raw.get("payload") or "")
        score = float(raw.get("score") or raw.get("relevance") or 0.0)
        extra = {k: v for k, v in raw.items() if k not in {"text", "content", "payload", "score", "relevance"}}
    elif hasattr(raw, "text"):
        payload = str(getattr(raw, "text", "") or "")
        score = float(getattr(raw, "score", 0.0) or 0.0)
        # Collect any extra attributes that look like metadata
        for attr in ("id", "dataset", "created_at", "chunk_index"):
            val = getattr(raw, attr, None)
            if val is not None:
                extra[attr] = val
    elif isinstance(raw, str):
        payload = raw
    else:
        logger.debug("Unrecognised Cognee result type: %s — skipping.", type(raw).__name__)
        return None

    if not payload.strip():
        logger.debug("Empty payload in Cognee result — skipping.")
        return None

    # -----------------------------------------------------------------------
    # Parse structured fields written by remember.py
    # -----------------------------------------------------------------------
    title = _extract_section(payload, *_TITLE_MARKERS)
    source = _extract_section(payload, *_SOURCE_MARKERS)
    link = _extract_section(payload, *_LINK_MARKERS)
    content = _extract_section(payload, *_CONTENT_MARKERS)

    # Fall-through: use the whole payload as content if we cannot parse fields
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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def recall_memories(query: str, limit: int = 8) -> list[MemoryItem]:
    """Retrieve normalised memories from Cognee relevant to *query*.

    This function is the **only** place in the codebase that calls
    ``cognee.recall()``.  All upstream callers (``memory_manager.py``) use
    this function; they never touch Cognee directly.

    Args:
        query: The user's natural-language question.
        limit: Maximum number of memories to return. Cognee may return fewer
               if fewer relevant memories exist.

    Returns:
        A list of :class:`MemoryItem` objects ordered by descending relevance.
        Returns an empty list when no memories are found or when Cognee is
        unavailable — callers must handle the empty case gracefully.

    Raises:
        RecallUnavailableError: When the Cognee SDK is not installed or its
            ``recall()`` API cannot be resolved.
        RecallExecutionError: When Cognee raises an exception during recall.
    """
    if not query or not query.strip():
        logger.warning("recall_memories() called with an empty query — returning [].")
        return []

    logger.info("Initiating Cognee recall for query: %.80r  (limit=%d)", query, limit)

    # ------------------------------------------------------------------
    # Resolve Cognee SDK
    # ------------------------------------------------------------------
    try:
        import cognee  # noqa: PLC0415 — intentional lazy import
    except ImportError as exc:
        raise RecallUnavailableError("Cognee SDK is not installed.") from exc

    recall_fn = getattr(cognee, "recall", None)
    if recall_fn is None:
        raise RecallUnavailableError("Cognee SDK does not expose a recall() API.")

    # ------------------------------------------------------------------
    # Execute recall
    # ------------------------------------------------------------------
    try:
        raw_results = recall_fn(query, top_k=limit)
        if inspect.isawaitable(raw_results):
            raw_results = await raw_results
    except RecallUnavailableError:
        raise
    except Exception as exc:
        logger.exception("Cognee recall() raised an unexpected exception.")
        raise RecallExecutionError(f"Cognee recall failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Guard: handle None or non-iterable returns
    # ------------------------------------------------------------------
    if raw_results is None:
        logger.info("Cognee recall() returned None — no memories found.")
        return []

    if not isinstance(raw_results, (list, tuple, Sequence)) or isinstance(raw_results, (str, bytes)):
        # Some Cognee versions wrap results in a generator or custom iterable
        try:
            raw_results = list(raw_results)
        except TypeError:
            logger.warning("Cognee recall() returned a non-iterable result — treating as empty.")
            return []

    # ------------------------------------------------------------------
    # Normalise
    # ------------------------------------------------------------------
    memories: list[MemoryItem] = []
    for idx, raw in enumerate(raw_results):
        item = _normalise_raw_result(raw)
        if item is not None:
            memories.append(item)
        else:
            logger.debug("Skipped un-normalisable result at index %d.", idx)

    logger.info(
        "Cognee recall complete — retrieved %d/%d normalisable memories.",
        len(memories),
        len(raw_results),
    )

    # Honour limit after normalisation (Cognee may not always respect it)
    return memories[:limit]
