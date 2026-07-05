"""
Phase 6 — Memory Lifecycle API

Exposes endpoints for triggering Cognee improvement cycles, inspecting memory health,
viewing improvement history, observing lifecycle events, forgetting nodes, and demonstrating
the evolution of memory over time.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional, Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

from app.services.cognee.memory_manager import MemoryManager
from app.services.cognee.forget import purge_node_memory
from app.services.analytics.improvement_service import ImprovementService
from app.services.analytics.memory_analyzer import MemoryAnalyzer
from app.services.analytics.lifecycle_tracker import LifecycleTracker
from app.storage.vector_db import get_vector_db
from app.api.schemas.memory_models import (
    GraphStatistics,
    MemoryHealthReport,
    ImprovementReport,
    MemoryEvolutionDemo,
    ImprovementHistoryResponse,
    RecallComparison,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_memory_manager = MemoryManager()
_improvement_service = ImprovementService()
_analyzer = MemoryAnalyzer()

# In-memory status tracker for background jobs
_improvement_status: dict = {"running": False, "last_triggered": None}
_legacy_memory_store: dict[str, Any] = {}


class LegacyMemoryValue(BaseModel):
    value: Any


@router.post("/{key}")
async def save_legacy_memory(key: str, payload: LegacyMemoryValue):
    """Simple key/value memory endpoint kept for the existing UI and tests."""
    _legacy_memory_store[key] = payload.value
    return {"status": "saved", "key": key}


@router.get("/vector")
async def get_vector_memories():
    """Return vector memory rows if the local vector table exists."""
    try:
        db = get_vector_db()
        table_names = db.table_names()
        if "memories" not in table_names:
            return {"memories": []}
        table = db.open_table("memories")
        return {"memories": table.to_lance().to_table().to_pylist()}
    except Exception as e:
        logger.debug("Unable to read vector memories: %s", e)
        return {"memories": []}


@router.delete("/cognee/{entity_id}")
async def delete_cognee_memory(entity_id: str):
    """Legacy purge endpoint used by the graph explorer."""
    success = await purge_node_memory(entity_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to purge memory.")
    return {"status": "success", "purged": entity_id}


@router.get("/{key}")
async def get_legacy_memory(key: str):
    """Read a value saved through the legacy key/value endpoint."""
    if key not in _legacy_memory_store:
        raise HTTPException(status_code=404, detail="Memory key not found.")
    return {"key": key, "value": _legacy_memory_store[key]}


@router.delete("/{key}")
async def delete_legacy_memory(key: str):
    """Delete a value saved through the legacy key/value endpoint."""
    if key not in _legacy_memory_store:
        raise HTTPException(status_code=404, detail="Memory key not found.")
    del _legacy_memory_store[key]
    return {"status": "deleted", "key": key}


# ---------------------------------------------------------------------------
# GET /memory/dashboard — Combined Phase 6 metrics (health + lifecycle)
# ---------------------------------------------------------------------------
@router.get("/dashboard")
async def get_dashboard():
    """Return high-level metrics for the Memory Explorer dashboard."""
    try:
        health = await _analyzer.get_health_report()
        lifecycle_stats = LifecycleTracker.get_stats()

        return {
            "total_memories": lifecycle_stats["total_ingested"],
            "total_entities": health.statistics.entities_count,
            "total_relationships": health.statistics.relationships_count,
            "datasets": ["news"],  # Chronos AI primarily uses the news dataset
            "graph_density": health.statistics.graph_density,
            "duplicate_estimation": health.statistics.orphan_nodes,
            "freshness": health.statistics.memory_freshness_score,
            "health_score": health.health_score,
            "health_status": health.status,
            "last_improvement": lifecycle_stats["last_improvement"],
            "last_ingestion": lifecycle_stats["last_ingestion"],
            "operation_counts": {
                "ingests": lifecycle_stats["total_ingested"],
                "recalls": lifecycle_stats["total_recalls"],
                "improvements": lifecycle_stats["total_improvements"],
                "forgets": lifecycle_stats["total_forgets"],
            }
        }
    except Exception as e:
        logger.exception("Failed to load dashboard metrics.")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# GET /memory/lifecycle — Memory event audit trail
# ---------------------------------------------------------------------------
@router.get("/lifecycle")
async def get_lifecycle(limit: int = 50):
    """Chronological history of all important memory events."""
    return {"events": LifecycleTracker.get_timeline(limit=limit)}


# ---------------------------------------------------------------------------
# GET /memory/debug — Intermediate pipeline trace for a query
# ---------------------------------------------------------------------------
@router.get("/debug")
async def get_debug_trace(
    query: str = Query(..., description="The user query to trace through the pipeline")
):
    """Executes a recall pipeline in debug mode and returns all intermediate steps."""
    try:
        result = await _memory_manager.ask(query, debug=True)
        return {
            "query": query,
            "retrieved_memories_count": result.memories_used,
            "retrieved_memories": result.memory_trace,
            "intermediate_pipeline_steps": result.debug_trace,
            "final_answer": result.answer,
            "sources": result.sources,
        }
    except Exception as e:
        logger.exception("Debug trace execution failed.")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# POST /memory/forget — Memory Forgetting
# ---------------------------------------------------------------------------
class ForgetRequest(BaseModel):
    entity_id: str

@router.post("/forget")
async def forget_memory(payload: ForgetRequest):
    """Forgets a memory entirely, removing it from Neo4j and Vector storage."""
    try:
        success = await _memory_manager.forget_memory(payload.entity_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to purge memory.")
        
        # After successful deletion, graph statistics are updated naturally via queries.
        return {
            "status": "success",
            "message": f"Successfully deleted references to '{payload.entity_id}'.",
            "entity": payload.entity_id,
        }
    except Exception as e:
        logger.exception("Memory forget operation failed.")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# GET /memory/graph-summary — Phase 6 raw statistics wrapper
# ---------------------------------------------------------------------------
@router.get("/graph-summary", response_model=GraphStatistics)
async def get_graph_summary():
    """Alias for returning raw graph statistics (entities, relationships, etc)."""
    try:
        return await _analyzer.analyze()
    except Exception as e:
        logger.exception("Failed to compute graph summary.")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# GET /memory/demo — Phase 6 Evolution Demo Wrapper
# ---------------------------------------------------------------------------
@router.get("/demo")
async def get_demo(
    topic: str = Query(default="OpenAI", description="Topic to demonstrate recall improvement on")
):
    """Executes a full before/after memory lifecycle demo."""
    return await get_evolution_demo(topic=topic)


# ---------------------------------------------------------------------------
# POST /memory/improve — Manually trigger improvement
# ---------------------------------------------------------------------------
@router.post("/improve")
async def trigger_improvement(
    background_tasks: BackgroundTasks,
    dataset: str = Query(default="news", description="Dataset to improve"),
):
    """Trigger a Cognee improve() cycle. Runs in the background and returns immediately."""
    if _improvement_status["running"]:
        return {
            "status": "already_running",
            "message": "An improvement cycle is already in progress.",
            "last_triggered": _improvement_status["last_triggered"],
        }

    _improvement_status["running"] = True
    _improvement_status["last_triggered"] = datetime.utcnow().isoformat()

    async def _run():
        try:
            await _memory_manager.improve_memory(dataset=dataset)
        except Exception as e:
            logger.error(f"Background improvement failed: {e}")
        finally:
            _improvement_status["running"] = False

    background_tasks.add_task(_run)

    return {
        "status": "started",
        "message": f"Memory improvement for dataset '{dataset}' started in the background.",
        "triggered_at": _improvement_status["last_triggered"],
    }


# ---------------------------------------------------------------------------
# GET /memory/improvement-status — Check if improvement is running
# ---------------------------------------------------------------------------
@router.get("/improvement-status")
async def get_improvement_status():
    """Check whether an improvement cycle is currently running."""
    return {
        "running": _improvement_status["running"],
        "last_triggered": _improvement_status["last_triggered"],
    }


# ---------------------------------------------------------------------------
# GET /memory/improvement-history — Past improvement runs
# ---------------------------------------------------------------------------
@router.get("/improvement-history", response_model=ImprovementHistoryResponse)
async def get_improvement_history(limit: int = Query(default=10, ge=1, le=50)):
    """Retrieve the history of past improvement cycles."""
    history = await _memory_manager.get_improvement_history()
    # Limit needs to be applied, though the history is loaded all at once above
    history = history[-limit:]
    return ImprovementHistoryResponse(
        history=history,
        total_runs=len(history),
        last_run_at=history[-1].finished_at if history else None,
    )


# ---------------------------------------------------------------------------
# GET /memory/health — Memory health score and recommendations
# ---------------------------------------------------------------------------
@router.get("/health", response_model=MemoryHealthReport)
async def get_memory_health():
    """Analyze and return the current memory graph health score."""
    try:
        return await _analyzer.get_health_report()
    except Exception as e:
        logger.exception("Failed to compute memory health.")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# GET /memory/statistics — Raw graph statistics (Legacy API alias)
# ---------------------------------------------------------------------------
@router.get("/statistics", response_model=GraphStatistics)
async def get_memory_statistics():
    """Return raw graph metrics: entities, relationships, density, orphans, freshness."""
    try:
        return await _analyzer.analyze()
    except Exception as e:
        logger.exception("Failed to compute graph statistics.")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# GET /memory/evolution — Graph comparison over last 2 runs
# ---------------------------------------------------------------------------
@router.get("/evolution")
async def get_memory_evolution():
    """Compare the last two improvement runs to show measurable graph improvement."""
    history = await _memory_manager.get_improvement_history()
    if len(history) < 2:
        return {
            "message": "At least 2 improvement runs are needed to show evolution.",
            "runs_completed": len(history),
        }

    prev = history[-2]
    latest = history[-1]
    return {
        "previous_run": {
            "timestamp": prev.finished_at,
            "entities": prev.after.entities_count,
            "relationships": prev.after.relationships_count,
        },
        "latest_run": {
            "timestamp": latest.finished_at,
            "entities": latest.after.entities_count,
            "relationships": latest.after.relationships_count,
        },
        "change": {
            "entity_delta": latest.after.entities_count - prev.after.entities_count,
            "relationship_delta": latest.after.relationships_count - prev.after.relationships_count,
            "density_delta": round(
                latest.after.graph_density - prev.after.graph_density, 4
            ),
        },
    }


# ---------------------------------------------------------------------------
# GET /memory/evolution/demo — Hackathon demo: full before-vs-after lifecycle
# ---------------------------------------------------------------------------
@router.get("/evolution/demo")
async def get_evolution_demo(
    topic: str = Query(default="OpenAI", description="Topic to demonstrate recall improvement on"),
):
    """
    Hackathon Demo Endpoint.

    Executes a complete memory enrichment lifecycle and returns a rich before-vs-after
    comparison: graph statistics, recall quality, health score change, and a human-readable
    explanation of what Cognee's improve() actually changed.
    """
    from app.services.cognee.recall import recall_memories

    logs: list[str] = []
    exec_start = datetime.utcnow()

    # --- Step 1: Capture BEFORE state ---
    logs.append("Step 1: Capturing baseline graph statistics...")
    before_stats = await _analyzer.analyze()
    before_health = await _analyzer.get_health_report()
    logs.append(f"  → Entities: {before_stats.entities_count}, Relationships: {before_stats.relationships_count}")
    logs.append(f"  → Health Score: {before_health.health_score}")

    # --- Step 2: Recall BEFORE improvement ---
    logs.append(f"Step 2: Running recall for '{topic}' BEFORE improve()...")
    try:
        memories_before = await recall_memories(topic, limit=8)
    except Exception:
        memories_before = []
    before_count = len(memories_before)
    before_titles = [m.title for m in memories_before]
    logs.append(f"  → Retrieved {before_count} memories before improvement.")

    # --- Step 3: Run improve() ---
    logs.append("Step 3: Triggering Cognee improve()...")
    report = await _memory_manager.improve_memory(dataset="news")
    logs.append(f"  → Improvement finished in {report.duration_seconds}s. Status: {report.status}")

    # --- Step 4: Recall AFTER improvement ---
    logs.append(f"Step 4: Running recall for '{topic}' AFTER improve()...")
    try:
        memories_after = await recall_memories(topic, limit=8)
    except Exception:
        memories_after = []
    after_count = len(memories_after)
    after_titles = [m.title for m in memories_after]
    logs.append(f"  → Retrieved {after_count} memories after improvement.")

    newly_discovered = [t for t in after_titles if t not in before_titles]
    logs.append(f"  → Newly discovered memories: {newly_discovered}")

    # --- Step 5: Capture AFTER state ---
    logs.append("Step 5: Capturing post-improvement graph statistics...")
    after_stats = report.after
    after_health = await _analyzer.get_health_report()
    logs.append(f"  → Entities: {after_stats.entities_count}, Relationships: {after_stats.relationships_count}")
    logs.append(f"  → Health Score: {after_health.health_score}")

    exec_time = (datetime.utcnow() - exec_start).total_seconds()

    # --- Build human-readable explanation ---
    rel_change = after_stats.relationships_count - before_stats.relationships_count
    dup_removed = report.removed_duplicates
    explanation_parts = [
        f"Cognee's improve() ran for {report.duration_seconds}s on the '{report.dataset}' dataset.",
        f"Relationships {'grew' if rel_change >= 0 else 'changed'} by {abs(rel_change)} ({'+' if rel_change >= 0 else ''}{rel_change}).",
        f"Estimated {dup_removed} duplicate or redundant concept(s) were consolidated.",
        f"Recall for '{topic}' returned {after_count - before_count:+d} more memories after enrichment.",
        f"Memory Health Score moved from {before_health.health_score} → {after_health.health_score}.",
    ]
    if newly_discovered:
        explanation_parts.append(f"Newly surfaced concepts: {', '.join(newly_discovered[:5])}.")

    return {
        "topic": topic,
        "total_demo_duration_seconds": round(exec_time, 2),
        "graph_before": {
            "entities": before_stats.entities_count,
            "relationships": before_stats.relationships_count,
            "graph_density": before_stats.graph_density,
            "health_score": before_health.health_score,
        },
        "graph_after": {
            "entities": after_stats.entities_count,
            "relationships": after_stats.relationships_count,
            "graph_density": after_stats.graph_density,
            "health_score": after_health.health_score,
        },
        "recall_comparison": {
            "query": topic,
            "before_recall_count": before_count,
            "after_recall_count": after_count,
            "newly_discovered_memories": newly_discovered,
            "improvement_delta": after_count - before_count,
        },
        "improvement_run": {
            "started_at": report.started_at.isoformat(),
            "duration_seconds": report.duration_seconds,
            "status": report.status,
            "new_relationships": report.new_relationships,
            "removed_duplicates": report.removed_duplicates,
            "strengthened_relationships": report.strengthened_relationships,
        },
        "explanation": " ".join(explanation_parts),
        "execution_logs": logs,
    }
