"""
RelationshipStrength: computes and updates edge weight scores in the graph.
Scores are updated using batched writes to avoid hammering the graph store.
"""
import logging
from typing import Optional
from app.storage.neo4j_graph import neo4j_graph

logger = logging.getLogger(__name__)


def compute_co_occurrence_strength(entities: list[str]) -> list[tuple[str, str, float]]:
    """
    Given a list of entities extracted from one article, compute pair-wise
    co-occurrence strength. Returns (source, target, strength) tuples.
    """
    pairs = []
    seen = list(dict.fromkeys(entities))  # deduplicate while preserving order
    for i, a in enumerate(seen):
        for b in seen[i + 1:]:
            pairs.append((a, b, 1.0))
    return pairs


def update_relationship_strengths(entity_batches: list[list[str]]) -> None:
    """
    Accept batches of entity lists (one per article) and increment co-occurrence
    edge weights in the graph store.
    """
    # Aggregate all pairs first, then write in batch
    strength_map: dict[tuple[str, str], float] = {}
    for entities in entity_batches:
        for src, tgt, weight in compute_co_occurrence_strength(entities):
            key = (src, tgt)
            strength_map[key] = strength_map.get(key, 0.0) + weight

    # Write to graph
    for (src, tgt), strength in strength_map.items():
        try:
            neo4j_graph.upsert_edge(src, tgt, "CO_OCCURS", {"strength": strength})
        except Exception as e:
            logger.warning(f"Failed to update relationship ({src}->{tgt}): {e}")

    logger.info(f"Updated {len(strength_map)} relationship strength pairs.")
