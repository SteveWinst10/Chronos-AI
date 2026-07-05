"""Public memory manager facade for the Chronos-AI backend.

Sole responsibility: orchestrate the retrieval pipeline by coordinating
``recall.py``, ``context_builder.py``, and ``llm_client.py``.

Rules
-----
- No Cognee imports.
- No prompt-building logic.
- No retrieval logic.
- Delegates every concern to the appropriate module.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Iterable, Mapping


from app.services.cognee.recall import (
    MemoryItem,
    RecallExecutionError,
    RecallUnavailableError,
    recall_memories,
)
from app.services.cognee.remember import RememberArticleResult, remember_article
from app.services.llm.llm_client import LLMClient
from app.services.retrieval.context_builder import build_context_prompt, get_system_prompt

# Phase 5 Imports
from app.services.analytics.improvement_service import ImprovementService
from app.services.analytics.memory_analyzer import MemoryAnalyzer
from app.api.schemas.memory_models import MemoryHealthReport, ImprovementReport, GraphStatistics

logger = logging.getLogger(__name__)

# Default number of memories to retrieve per question.
_DEFAULT_RECALL_LIMIT: int = 8


# ---------------------------------------------------------------------------
# Typed return shape for ask()
# ---------------------------------------------------------------------------

class AskResult:
    """Structured result from memory_manager.ask().

    Attributes:
        answer:        LLM-generated answer grounded in retrieved memories.
        sources:       Deduplicated list of (title, source, link) dicts,
                       one entry per memory that was passed to the LLM.
        memories_used: Total number of memories retrieved from Cognee and
                       included in the context prompt.
        memory_trace:  Detailed list of retrieved memory metadata for
                       hackathon judges — proves the answer came from Cognee.
    """

    __slots__ = ("answer", "sources", "memories_used", "memory_trace")

    def __init__(
        self,
        answer: str,
        sources: list[dict[str, str]],
        memories_used: int,
        memory_trace: list[dict[str, Any]],
    ) -> None:
        self.answer = answer
        self.sources = sources
        self.memories_used = memories_used
        self.memory_trace = memory_trace

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "sources": self.sources,
            "memories_used": self.memories_used,
            "memory_trace": self.memory_trace,
        }


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _build_sources(memories: list[MemoryItem]) -> list[dict[str, str]]:
    """Deduplicate and serialise source references from retrieved memories."""
    seen: set[str] = set()
    sources: list[dict[str, str]] = []
    for memory in memories:
        key = memory.link or memory.title
        if key and key not in seen:
            seen.add(key)
            sources.append(
                {
                    "title": memory.title,
                    "source": memory.source,
                    "link": memory.link,
                }
            )
    return sources


def _build_memory_trace(memories: list[MemoryItem]) -> list[dict[str, Any]]:
    """Build the memory_trace payload for hackathon demo / debugging.

    Shows judges that the answer was grounded in specific Cognee memories,
    not the base LLM's pretrained knowledge.
    """
    trace: list[dict[str, Any]] = []
    for idx, memory in enumerate(memories, start=1):
        trace.append(
            {
                "rank": idx,
                "title": memory.title,
                "source": memory.source,
                "link": memory.link,
                "relevance_score": memory.score,
                "content_preview": memory.content[:200] + "…" if len(memory.content) > 200 else memory.content,
                "metadata": memory.metadata,
            }
        )
    return trace


# ---------------------------------------------------------------------------
# Facade class
# ---------------------------------------------------------------------------


class MemoryManager:
    """Clean interface for all Cognee memory operations in the backend."""
 
    _ingestion_count = 0
    _IMPROVE_THRESHOLD = 25
 
    @property
    def ingestion_count(self) -> int:
        return MemoryManager._ingestion_count
 
    def _increment_ingestion_count(self):
        MemoryManager._ingestion_count += 1

    # ------------------------------------------------------------------
    # Ingestion (Phase 1)
    # ------------------------------------------------------------------

    async def remember_article(self, article: Mapping[str, Any]) -> RememberArticleResult:
        """Store one parsed news article in Cognee.

        Args:
            article: Parsed article with ``title``, ``content``, ``source``,
                     and ``link`` keys.

        Returns:
            Structured ingestion result from the Cognee remember pipeline.
        """
        result = await remember_article(article)

        # Phase 5: Auto-improvement hook — every N articles trigger improve()
        self._increment_ingestion_count()
        if MemoryManager._ingestion_count >= self._IMPROVE_THRESHOLD:
            MemoryManager._ingestion_count = 0
            logger.info("Auto-improvement threshold reached — scheduling background improve().")
            asyncio.create_task(self.improve_memory())

        return result


    async def remember_articles(
        self,
        articles: Iterable[Mapping[str, Any]],
    ) -> list[RememberArticleResult]:
        """Store multiple parsed news articles in Cognee.

        Args:
            articles: Iterable of parsed article mappings.

        Returns:
            A result for each article, in input order.
        """
        results: list[RememberArticleResult] = []
        for article in articles:
            results.append(await self.remember_article(article))
        return results

    # ------------------------------------------------------------------
    # Retrieval (Phase 2)
    # ------------------------------------------------------------------

    async def ask(
        self,
        question: str,
        *,
        recall_limit: int = _DEFAULT_RECALL_LIMIT,
    ) -> AskResult:
        """Answer a question using only memories retrieved from Cognee.

        Orchestration flow:
            1. ``recall_memories(question)``     → list[MemoryItem]
            2. ``build_context_prompt(…)``       → prompt string
            3. ``LLMClient.get_completion(…)``   → answer string
            4. Build and return :class:`AskResult`.

        Args:
            question:     The user's natural-language question.
            recall_limit: How many memories to request from Cognee.

        Returns:
            :class:`AskResult` with ``answer``, ``sources``,
            ``memories_used``, and ``memory_trace``.
        """
        logger.info("MemoryManager.ask() — question: %.100r", question)

        # Step 1 — Retrieve memories from Cognee
        memories: list[MemoryItem] = []
        retrieval_error: str | None = None

        try:
            memories = await recall_memories(question, limit=recall_limit)
        except RecallUnavailableError as exc:
            logger.error("Cognee recall unavailable: %s", exc)
            retrieval_error = str(exc)
        except RecallExecutionError as exc:
            logger.error("Cognee recall execution error: %s", exc)
            retrieval_error = str(exc)
        except Exception as exc:
            logger.exception("Unexpected error during Cognee recall.")
            retrieval_error = f"Unexpected retrieval error: {exc}"

        logger.info(
            "Recall complete — %d memories retrieved%s.",
            len(memories),
            f" (error: {retrieval_error})" if retrieval_error else "",
        )

        # Step 2 — Build the context prompt (pure function, no I/O)
        context_prompt = build_context_prompt(question, memories)
        system_prompt = get_system_prompt()

        # Step 3 — Call the LLM with the memory-grounded prompt
        llm = LLMClient()
        try:
            answer = await llm.get_completion(context_prompt, system_prompt)
        except Exception as exc:
            logger.exception("LLM completion failed during ask().")
            answer = f"LLM error — could not generate an answer: {exc}"

        # Step 4 — Build structured result
        sources = _build_sources(memories)
        memory_trace = _build_memory_trace(memories)

        result = AskResult(
            answer=answer,
            sources=sources,
            memories_used=len(memories),
            memory_trace=memory_trace,
        )

        logger.info(
            "ask() complete — memories_used=%d, answer_len=%d.",
            result.memories_used,
            len(result.answer),
        )

        return result

    # ------------------------------------------------------------------
    # Self-Improvement (Phase 5)
    # ------------------------------------------------------------------

    async def improve_memory(self, dataset: str = "news") -> ImprovementReport:
        """Trigger an enrichment cycle via improve()/memify()."""
        service = ImprovementService()
        return await service.run_improvement(dataset=dataset)

    async def get_memory_health(self) -> MemoryHealthReport:
        """Analyze current graph state and return health metrics."""
        analyzer = MemoryAnalyzer()
        return await analyzer.get_health_report()

    async def get_memory_statistics(self) -> GraphStatistics:
        """Retrieve raw graph statistics."""
        analyzer = MemoryAnalyzer()
        return await analyzer.analyze()

    async def get_improvement_history(self) -> list[ImprovementReport]:
        """Retrieve past improvement logs."""
        service = ImprovementService()
        return await service.get_history()
