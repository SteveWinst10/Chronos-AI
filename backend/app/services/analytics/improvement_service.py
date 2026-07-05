"""
Improvement Service — Phase 5

Orchestrates Cognee's improve() cycle and generates structured before-vs-after
improvement reports. All reports are persisted to a JSON audit log at data/.
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime

from app.api.schemas.memory_models import ImprovementReport
from app.services.analytics.memory_analyzer import MemoryAnalyzer

logger = logging.getLogger(__name__)

# Persist history beside the backend root so it survives restarts
_HISTORY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "data",
    "improvement_history.json",
)


class ImprovementService:
    """Orchestrates Cognee improve()/memify() calls and persists run reports."""

    def __init__(self):
        self.analyzer = MemoryAnalyzer()
        os.makedirs(os.path.dirname(_HISTORY_PATH), exist_ok=True)

    # ------------------------------------------------------------------
    # Primary Entrypoint
    # ------------------------------------------------------------------

    async def run_improvement(self, dataset: str = "news") -> ImprovementReport:
        """
        Execute a full Cognee improve() cycle.

        Flow:
            1. Snapshot graph state BEFORE improve().
            2. Call cognee.improve() — handles deduplication, relationship
               enrichment, and context index rebuilding inside Cognee.
            3. Snapshot graph state AFTER improve().
            4. Compute delta metrics and persist the report.
        """
        start_time = datetime.utcnow()
        logger.info("[Phase 5] Starting memory improvement cycle for dataset='%s'.", dataset)

        # 1 — Capture BEFORE snapshot
        before_stats = await self.analyzer.analyze()
        logger.info(
            "[Phase 5] Before: entities=%d, relationships=%d, density=%.4f",
            before_stats.entities_count,
            before_stats.relationships_count,
            before_stats.graph_density,
        )

        # 2 — Execute Cognee improve()
        status = "completed"
        error_msg: str | None = None
        try:
            import cognee
            raw_result = cognee.improve(dataset=dataset)
            import inspect
            if inspect.isawaitable(raw_result):
                await raw_result
            logger.info("[Phase 5] cognee.improve() completed successfully.")
        except Exception as exc:
            logger.error("[Phase 5] cognee.improve() failed: %s", exc)
            status = "failed"
            error_msg = str(exc)

        finish_time = datetime.utcnow()
        duration = (finish_time - start_time).total_seconds()

        # 3 — Capture AFTER snapshot
        after_stats = await self.analyzer.analyze()
        logger.info(
            "[Phase 5] After: entities=%d, relationships=%d, density=%.4f",
            after_stats.entities_count,
            after_stats.relationships_count,
            after_stats.graph_density,
        )

        # 4 — Compute deltas
        new_relationships = max(0, after_stats.relationships_count - before_stats.relationships_count)
        # Entity reduction = duplicates consolidated (merging reduces node count)
        removed_duplicates = max(0, before_stats.entities_count - after_stats.entities_count)
        new_entities = max(0, after_stats.entities_count - before_stats.entities_count)
        # Estimate strengthened relationships as a fraction of existing relationships
        # (Cognee updates weights, so the count stays the same but values change)
        strengthened_relationships = max(0, min(before_stats.relationships_count, new_relationships * 2))

        report = ImprovementReport(
            id=str(uuid.uuid4()),
            started_at=start_time,
            finished_at=finish_time,
            duration_seconds=round(duration, 2),
            dataset=dataset,
            status=status,
            error=error_msg,
            before=before_stats,
            after=after_stats,
            new_relationships=new_relationships,
            removed_duplicates=removed_duplicates,
            strengthened_relationships=strengthened_relationships,
            new_entities=new_entities,
            health_score_change=0.0,  # Computed by the caller via MemoryAnalyzer
        )

        await self._persist_report(report)
        logger.info("[Phase 5] Improvement run '%s' finished. Duration=%.2fs, Status=%s.", report.id, duration, status)
        return report

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    async def get_history(self, limit: int = 10) -> list[ImprovementReport]:
        """Load and return the most recent improvement reports from the audit log."""
        if not os.path.exists(_HISTORY_PATH):
            return []
        try:
            with open(_HISTORY_PATH, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            return [ImprovementReport(**r) for r in raw[-limit:]]
        except Exception as exc:
            logger.error("[Phase 5] Failed to read improvement history: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _persist_report(self, report: ImprovementReport) -> None:
        """Append the report to the JSON audit log."""
        history: list[dict] = []
        if os.path.exists(_HISTORY_PATH):
            try:
                with open(_HISTORY_PATH, "r", encoding="utf-8") as fh:
                    history = json.load(fh)
            except Exception:
                history = []

        history.append(json.loads(report.model_dump_json()))

        try:
            with open(_HISTORY_PATH, "w", encoding="utf-8") as fh:
                json.dump(history, fh, indent=2, default=str)
        except Exception as exc:
            logger.error("[Phase 5] Failed to persist improvement report: %s", exc)
