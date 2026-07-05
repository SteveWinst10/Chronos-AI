"""
RelationshipDiscovery & Strength: discovers connections and calculates confidence scores.
Exposes how entities like 'OpenAI' and 'Microsoft' are related based on Cognee's graph.
"""
import logging
from typing import Any, Optional
from app.storage.neo4j_graph import neo4j_graph

logger = logging.getLogger(__name__)


class RelationshipDiscovery:
    """Service to explore the graph and calculate relationship strengths."""

    @staticmethod
    async def discover_connections(entity_name: str) -> list[dict[str, Any]]:
        """
        [PHASE 3] Discovers all connected entities and relationships already in Cognee.
        Organises them by type and calculates a strength score for each.
        """
        logger.info(f"Discovering connections for: {entity_name}")
        
        # 1. Get raw neighborhood from Neo4j/Mock
        # We rely on the storage layer methods implemented in Phase 3
        neighbors = neo4j_graph.get_neighbors(entity_name)
        
        if not neighbors:
            logger.info(f"No connections found for {entity_name}.")
            return []

        # 2. Process and calculate strength
        results = []
        for n in neighbors:
            # Strength factors: 
            # - Frequency (if stored in properties)
            # - Recency (based on 'last_seen' metadata if exists)
            # - Relationship type weight
            
            raw_strength = n.get("properties", {}).get("strength", 0.5)
            # Normalize strength between 0.0 and 1.0
            strength = min(max(float(raw_strength), 0.1), 1.0)
            
            # Recency boost (simulated or from metadata)
            last_seen = n.get("properties", {}).get("last_seen")
            if last_seen:
                # Logic to decay strength over time could go here
                pass

            results.append({
                "entity": n["target"] if n["source"] == entity_name else n["source"],
                "relationship": n["type"],
                "strength": round(strength, 2),
                "label": n["target_label"] if n["source"] == entity_name else n["source_label"],
                "metadata": n.get("properties", {})
            })

        # Sort by strength descending
        results.sort(key=lambda x: x["strength"], reverse=True)
        
        logger.info(f"Discovery complete: {len(results)} relations found for {entity_name}.")
        return results

    @staticmethod
    async def get_relationship_path(source: str, target: str) -> list[str]:
        """Finds the shortest path between two entities in the graph."""
        return neo4j_graph.shortest_path(source, target)

    @staticmethod
    async def get_entity_centrality(entity_name: str) -> dict[str, Any]:
        """Uses node degree as a proxy for how 'trending' or 'central' an entity is."""
        degree = neo4j_graph.entity_degree(entity_name)
        return {
            "entity": entity_name,
            "centrality_score": degree,
            "significance": "High" if degree > 10 else "Medium" if degree > 3 else "Low"
        }
