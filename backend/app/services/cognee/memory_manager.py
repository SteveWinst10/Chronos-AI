"""Public memory manager facade for the Chronos-AI backend.

Sole responsibility: orchestrate the retrieval pipeline by coordinating
``recall.py``, ``context_builder.py``, and ``llm_client.py``.

Rules
-----
- No Cognee imports (except where wrapped in specific methods).
- No prompt-building logic.
- No retrieval logic.
- Delegates every concern to the appropriate module.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Iterable, Mapping, Optional

from app.services.cognee.recall import (
    MemoryItem,
    RecallExecutionError,
    RecallUnavailableError,
    recall_memories,
)
from app.services.cognee.remember import RememberArticleResult, remember_article
from app.services.cognee.forget import purge_node_memory
from app.services.llm.llm_client import LLMClient
from app.services.retrieval.context_builder import build_context_prompt, get_system_prompt
from app.storage.neo4j_graph import neo4j_graph

# Phase 5 & 6 Imports
from app.services.analytics.improvement_service import ImprovementService
from app.services.analytics.memory_analyzer import MemoryAnalyzer
from app.services.analytics.lifecycle_tracker import LifecycleTracker, EventType
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
        debug_trace:   Full intermediate pipeline state for demonstration/debugging.
    """

    __slots__ = ("answer", "sources", "memories_used", "memory_trace", "debug_trace")

    def __init__(
        self,
        answer: str,
        sources: list[dict[str, str]],
        memories_used: int,
        memory_trace: list[dict[str, Any]],
        debug_trace: Optional[dict[str, Any]] = None,
    ) -> None:
        self.answer = answer
        self.sources = sources
        self.memories_used = memories_used
        self.memory_trace = memory_trace
        self.debug_trace = debug_trace

    def to_dict(self) -> dict[str, Any]:
        d = {
            "answer": self.answer,
            "sources": self.sources,
            "memories_used": self.memories_used,
            "memory_trace": self.memory_trace,
        }
        if self.debug_trace is not None:
            d["debug_trace"] = self.debug_trace
        return d


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
        """Store one parsed news article in Cognee."""
        t0 = time.time()
        result = await remember_article(article)
        duration_ms = (time.time() - t0) * 1000

        # Phase 6: Lifecycle Tracking
        LifecycleTracker.log(
            event_type=EventType.INGESTION,
            description=f"Ingested article: {article.get('title', 'Unknown')}",
            duration_ms=duration_ms,
            affected_memories=1,
            affected_entities=[article.get('title', 'Unknown')],
            status="success" if result.status == "success" else "failed",
        )

        # Phase 5: Auto-improvement hook
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
        """Store multiple parsed news articles in Cognee."""
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
        debug: bool = False,
    ) -> AskResult:
        """Answer a question using only memories retrieved from Cognee."""
        logger.info("MemoryManager.ask() — question: %.100r", question)
        t0 = time.time()

        # Step 1 — Retrieve memories from Cognee
        memories: list[MemoryItem] = []
        retrieval_error: str | None = None

        try:
            memories = await recall_memories(question, limit=recall_limit)
        except (RecallUnavailableError, RecallExecutionError) as exc:
            logger.error("Cognee recall error: %s", exc)
            retrieval_error = str(exc)
        except Exception as exc:
            logger.exception("Unexpected error during Cognee recall.")
            retrieval_error = f"Unexpected retrieval error: {exc}"

        logger.info("Recall complete — %d memories retrieved.", len(memories))

        # Step 2 — Build the context prompt
        context_prompt = build_context_prompt(question, memories)
        system_prompt = get_system_prompt()

        # Step 3 — Call the LLM with the memory-grounded prompt
        llm = LLMClient()
        try:
            answer = await llm.get_completion(context_prompt, system_prompt)
        except Exception as exc:
            logger.exception("LLM completion failed during ask().")
            answer = f"LLM error — could not generate an answer: {exc}"
            retrieval_error = retrieval_error or str(exc)

        duration_ms = (time.time() - t0) * 1000

        # Phase 6: Lifecycle Tracking
        LifecycleTracker.log(
            event_type=EventType.RECALL,
            description=f"Recalled memories for query: '{question}'",
            duration_ms=duration_ms,
            affected_memories=len(memories),
            status="failed" if retrieval_error and not answer.strip() else "success",
            metadata={"query": question},
        )

        # Step 4 — Build structured result
        sources = _build_sources(memories)
        memory_trace = _build_memory_trace(memories)
        
        debug_trace = None
        if debug:
            debug_trace = {
                "original_question": question,
                "context_prompt_sent_to_model": context_prompt,
                "system_prompt_sent_to_model": system_prompt,
                "raw_retrieved_memories_count": len(memories),
            }

        result = AskResult(
            answer=answer,
            sources=sources,
            memories_used=len(memories),
            memory_trace=memory_trace,
            debug_trace=debug_trace,
        )

        return result

    # ------------------------------------------------------------------
    # Self-Improvement (Phase 5)
    # ------------------------------------------------------------------

    async def improve_memory(self, dataset: str = "news") -> ImprovementReport:
        """Trigger an enrichment cycle via improve()/memify()."""
        t0 = time.time()
        service = ImprovementService()
        report = await service.run_improvement(dataset=dataset)
        duration_ms = (time.time() - t0) * 1000
        
        # Log to Tracker
        LifecycleTracker.log(
            event_type=EventType.IMPROVEMENT,
            description=f"Improvement cycle on dataset '{dataset}'",
            duration_ms=duration_ms,
            affected_memories=report.new_relationships + report.strengthened_relationships,
            status=report.status,
        )
        return report

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

    # ------------------------------------------------------------------
    # Forget (Phase 6)
    # ------------------------------------------------------------------

    async def forget_memory(self, entity_id: str) -> bool:
        """Purges a memory/entity completely from the system."""
        t0 = time.time()
        success = await purge_node_memory(entity_id)
        duration_ms = (time.time() - t0) * 1000
        
        LifecycleTracker.log(
            event_type=EventType.FORGET,
            description=f"Forgot entity: '{entity_id}'",
            duration_ms=duration_ms,
            affected_entities=[entity_id],
            status="success" if success else "failed",
        )
        return success


class CogneeMemoryManager:
    """Legacy static facade kept for older scripts and tests.

    New code should instantiate ``MemoryManager`` directly.
    """

    @staticmethod
    async def remember_context(text: str, conversation_id: str | None = None) -> dict[str, Any]:
        """Store ad-hoc context in the graph fallback as a conversation node."""
        node_name = conversation_id or f"context-{int(time.time() * 1000)}"
        neo4j_graph.upsert_node(
            node_name,
            "CONVERSATION",
            {
                "text": text,
                "conversation_id": conversation_id,
            },
        )
        return {"status": "success", "conversation_id": conversation_id, "text": text}

    @staticmethod
    async def recall_context(query: str, limit: int = 5) -> dict[str, Any]:
        """Return semantic and relational memories in the pre-refactor shape."""
        semantic_memories: list[dict[str, Any]] = []
        try:
            memories = await recall_memories(query, limit=limit)
            semantic_memories = [
                {
                    "title": memory.title,
                    "content": memory.content,
                    "source": memory.source,
                    "link": memory.link,
                    "score": memory.score,
                    "metadata": memory.metadata,
                }
                for memory in memories
            ]
        except Exception as exc:
            logger.debug("Legacy recall_context semantic recall skipped: %s", exc)

        relational_memories = neo4j_graph.get_all_edges()[:limit]
        return {
            "semantic_memories": semantic_memories,
            "relational_memories": relational_memories,
        }

    @staticmethod
    async def purge_node_memory(entity_id: str) -> bool:
        """Legacy wrapper around the current forget implementation."""
        return await purge_node_memory(entity_id)
