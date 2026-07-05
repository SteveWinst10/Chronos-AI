"""
TrendDetector: analyzes graph topology to identify trending topics and entities.
Uses node centrality (degree) and relationship density to spot 'hot' subjects.
"""
from __future__ import annotations

import logging
from datetime import datetime, UTC
from typing import Any
from app.storage.neo4j_graph import neo4j_graph

logger = logging.getLogger(__name__)


class TrendDetector:
    """Service to detect trends and 'fastest growing' topics in the news memory."""

    @staticmethod
    async def get_trending_report() -> dict[str, Any]:
        """
        [PHASE 3] Analyzes the entire graph to detect trends.
        - Most discussed: Highest node degrees.
        - Emerging: Relationship frequency spikes.
        """
        logger.info("Generating Trend Report...")

        # 1. Fetch all nodes to calculate centrality
        all_nodes = neo4j_graph.get_all_nodes()
        
        if not all_nodes:
            logger.info("Empty graph — no trends detected.")
            return {
                "most_discussed_companies": [],
                "top_topics": [],
                "most_connected_entity": "N/A",
                "relationship_summary": []
            }

        # Calculate degree for each node
        node_metrics = []
        for node in all_nodes:
            name = node["name"]
            degree = neo4j_graph.entity_degree(name)
            node_metrics.append({
                "name": name,
                "label": node["label"],
                "degree": degree
            })

        # 2. Categorise and Sort
        # Filter for companies/orgs
        companies = [n for n in node_metrics if n["label"].upper() in ("COMPANY", "ORGANIZATION", "ORG")]
        # If no specific labels, use all as generic concepts
        if not companies:
            companies = node_metrics
            
        companies.sort(key=lambda x: x["degree"], reverse=True)

        topics = [n for n in node_metrics if n["label"].upper() in ("TOPIC", "CONCEPT", "CATEGORY")]
        if not topics:
            topics = node_metrics
            
        topics.sort(key=lambda x: x["degree"], reverse=True)

        # 3. Relationship Patterns
        rel_freq = neo4j_graph.relationship_frequency()

        return {
            "most_discussed_companies": [c["name"] for c in companies[:5]],
            "top_topics": [t["name"] for t in topics[:5]],
            "most_connected_entity": companies[0]["name"] if companies else "N/A",
            "relationship_summary": rel_freq[:5],
            "timestamp": datetime.now(UTC).isoformat()
        }
