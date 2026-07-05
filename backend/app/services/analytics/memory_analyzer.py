"""
Memory Analyzer — Phase 5

Computes graph-theoretic health metrics from the existing storage layer (neo4j_graph
singleton). Falls back gracefully when Neo4j is unavailable (mock store is used
transparently by Neo4jGraphStore).

No external dependencies beyond app.storage.neo4j_graph.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from app.api.schemas.memory_models import GraphStatistics, MemoryHealthReport
from app.storage.neo4j_graph import neo4j_graph

logger = logging.getLogger(__name__)

# --- Weight constants for the health score (must sum to 1.0) ---
_W_COVERAGE      = 0.20
_W_FRESHNESS     = 0.20
_W_CONNECTIVITY  = 0.30
_W_DEDUP         = 0.15
_W_STRENGTH      = 0.15


class MemoryAnalyzer:
    """
    Analyzes the current state of the Cognee knowledge graph and returns
    structured metrics for health scoring and improvement tracking.
    """

    # ------------------------------------------------------------------
    # Core Analysis
    # ------------------------------------------------------------------

    async def analyze(self) -> GraphStatistics:
        """Compute all graph metrics and return a GraphStatistics snapshot."""
        try:
            all_nodes = neo4j_graph.get_all_nodes()
            all_edges = neo4j_graph.get_all_edges()

            entity_count = len(all_nodes)
            relationship_count = len(all_edges)

            # ---- Graph Density ----
            # Ratio of actual edges to all possible edges in an undirected graph.
            possible_edges = (entity_count * (entity_count - 1)) / 2 if entity_count > 1 else 1
            density = round((relationship_count / possible_edges) * 100, 4) if possible_edges else 0.0

            # ---- Degree Stats ----
            degree_map: dict[str, int] = {n["name"]: 0 for n in all_nodes}
            for edge in all_edges:
                if edge["source"] in degree_map:
                    degree_map[edge["source"]] += 1
                if edge["target"] in degree_map:
                    degree_map[edge["target"]] += 1

            avg_degree = round(sum(degree_map.values()) / entity_count, 2) if entity_count else 0.0
            orphan_count = sum(1 for d in degree_map.values() if d == 0)

            most_connected = max(degree_map, key=degree_map.get) if degree_map else None
            least_connected = min(degree_map, key=degree_map.get) if degree_map else None

            # ---- Duplicate Ratio ----
            # Estimated from ratio of orphan nodes (concepts that were merged will
            # reduce orphan count in subsequent runs, serving as a proxy for dedup).
            duplicate_ratio = round(orphan_count / entity_count, 3) if entity_count else 0.0

            # ---- Freshness ----
            # Derived from 'last_updated' properties on nodes if they exist.
            # Falls back to a neutral 0.85 score if timestamps are absent.
            freshness = self._compute_freshness(all_nodes)

            # ---- Memory Count (approximate from edges as proxy for documents) ----
            # Without direct access to Cognee's document store, we estimate
            # memory count as 2x unique relationship types (each article ≈ 2 relations).
            memory_count = max(entity_count, relationship_count)

            return GraphStatistics(
                memory_count=memory_count,
                entities_count=entity_count,
                relationships_count=relationship_count,
                graph_density=density,
                duplicate_ratio=duplicate_ratio,
                orphan_nodes=orphan_count,
                average_degree=avg_degree,
                memory_freshness_score=freshness,
                most_connected_entity=most_connected,
                least_connected_entity=least_connected,
            )

        except Exception as e:
            logger.error(f"Memory analysis failed: {e}")
            return GraphStatistics(
                memory_count=0,
                entities_count=0,
                relationships_count=0,
                graph_density=0.0,
                duplicate_ratio=0.0,
                orphan_nodes=0,
                average_degree=0.0,
                memory_freshness_score=0.0,
            )

    # ------------------------------------------------------------------
    # Health Report
    # ------------------------------------------------------------------

    async def get_health_report(self) -> MemoryHealthReport:
        """Compute the weighted memory health score and recommendations."""
        stats = await self.analyze()
        score = self._compute_health_score(stats)

        status = "Healthy"
        if score < 50:
            status = "Degraded"
        elif score < 70:
            status = "Needs Improvement"

        recommendations: list[str] = []
        if stats.duplicate_ratio > 0.15:
            recommendations.append("Run improve() to consolidate duplicate entity concepts.")
        if stats.orphan_nodes > max(1, stats.entities_count * 0.10):
            recommendations.append("Many orphan nodes detected — consider refining entity extraction.")
        if stats.average_degree < 2.0 and stats.entities_count > 5:
            recommendations.append("Low graph connectivity — ingest more articles to enrich relationships.")
        if stats.memory_freshness_score < 0.5:
            recommendations.append("Memory is getting stale — run a fresh news ingestion pipeline.")

        return MemoryHealthReport(
            health_score=round(score, 1),
            statistics=stats,
            status=status,
            recommendations=recommendations,
        )

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _compute_health_score(self, stats: GraphStatistics) -> float:
        """
        Weighted health score formula (0–100):
            Health = (0.20 × Coverage)
                   + (0.20 × Freshness)
                   + (0.30 × Connectivity)
                   + (0.15 × DuplicateReduction)
                   + (0.15 × Strength)

        Definitions:
            Coverage         = clamp(entities / max(1, memory_count) × 50, 0, 100)
                               (Assumes ≈2 entities per memory article is healthy baseline)
            Freshness        = memory_freshness_score × 100
            Connectivity     = clamp(average_degree / 10 × 100, 0, 100)
                               (Assumes avg_degree of 10 is very well-connected)
            DuplicateReduction = (1 - duplicate_ratio) × 100
            Strength         = (1 - orphan_ratio) × 100
        """
        entity_count = max(1, stats.entities_count)
        memory_count = max(1, stats.memory_count)

        coverage    = min(100.0, (entity_count / memory_count) * 50)
        freshness   = stats.memory_freshness_score * 100
        connectivity = min(100.0, (stats.average_degree / 10.0) * 100)
        dedup       = (1.0 - stats.duplicate_ratio) * 100
        orphan_ratio = stats.orphan_nodes / entity_count
        strength    = (1.0 - orphan_ratio) * 100

        score = (
            _W_COVERAGE     * coverage
            + _W_FRESHNESS  * freshness
            + _W_CONNECTIVITY * connectivity
            + _W_DEDUP      * dedup
            + _W_STRENGTH   * strength
        )
        return max(0.0, min(100.0, score))

    def _compute_freshness(self, all_nodes: list[dict]) -> float:
        """
        Derive a freshness score from node timestamps if available.
        Returns 0.0–1.0. Falls back to 0.85 if no timestamps found.
        """
        now = datetime.now(tz=timezone.utc).timestamp()
        one_week_secs = 7 * 24 * 3600
        two_weeks_secs = 14 * 24 * 3600

        fresh_count = 0
        dated_count = 0

        for node in all_nodes:
            ts = node.get("properties", {}).get("created_at") or node.get("properties", {}).get("last_seen")
            if ts:
                dated_count += 1
                try:
                    if isinstance(ts, (int, float)):
                        age = now - ts
                    else:
                        from dateutil import parser as dp
                        age = now - dp.parse(str(ts)).timestamp()
                    if age <= one_week_secs:
                        fresh_count += 1
                    elif age <= two_weeks_secs:
                        fresh_count += 0.5  # partial credit
                except Exception:
                    pass

        if dated_count == 0:
            # No timestamp metadata — assume fresh since we just ingested
            return 0.85

        return round(fresh_count / dated_count, 3)
