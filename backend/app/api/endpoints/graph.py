from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from app.services.analytics.relationship_strength import RelationshipDiscovery
from app.storage.neo4j_graph import neo4j_graph

router = APIRouter(prefix="/graph", tags=["Knowledge Graph"])
logger = logging.getLogger(__name__)

@router.get("/")
async def graph_snapshot():
    """Returns actual Neo4j graph nodes and edges for visualization."""
    nodes = neo4j_graph.get_all_nodes()
    # Note: ensure get_all_edges exists or fall back
    edges = getattr(neo4j_graph, "get_all_edges", lambda: [])()
    return {
        "nodes": nodes,
        "edges": edges
    }

@router.get("/entity/{name}")
async def get_entity_details(name: str):
    """Fetch structured metadata and centrality for a single entity."""
    start_time = time.time()
    entity = neo4j_graph.get_entity(name)
    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity '{name}' not found in graph memory.")
    
    centrality = await RelationshipDiscovery.get_entity_centrality(name)
    
    logger.info(
        "GET /graph/entity/%s — ExecTime: %.2fms", 
        name, (time.time() - start_time) * 1000
    )
    
    return {
        "entity": entity,
        "metrics": centrality
    }

@router.get("/neighbors/{name}")
async def get_neighbors(name: str):
    """Fetch all connected nodes and relationships for an entity."""
    start_time = time.time()
    connections = await RelationshipDiscovery.discover_connections(name)
    
    logger.info(
        "GET /graph/neighbors/%s — Found nodes: %d — ExecTime: %.2fms",
        name, len(connections), (time.time() - start_time) * 1000
    )
    
    return {
        "entity": name,
        "connections": connections
    }

@router.get("/path/{source}/{target}")
async def get_shortest_path(source: str, target: str):
    """Discover how two entities are connected (shortest path)."""
    start_time = time.time()
    path = await RelationshipDiscovery.get_relationship_path(source, target)
    
    logger.info(
        "GET /graph/path/%s -> %s — ExecTime: %.2fms",
        source, target, (time.time() - start_time) * 1000
    )
    
    return {
        "source": source,
        "target": target,
        "path": path,
        "connected": len(path) > 0
    }

@router.get("/search")
async def search_graph(q: str = Query(..., min_length=2)):
    """Search for entities in the graph matching the query string."""
    # This searches the persistent graph nodes
    all_nodes = neo4j_graph.get_all_nodes()
    matches = [n for n in all_nodes if q.lower() in n["name"].lower()]
    return {
        "query": q,
        "matches": matches[:10]
    }

@router.get("/trends")
async def get_trends():
    """Identify trending companies, concepts, and connection patterns."""
    from app.services.analytics.trend_detector import TrendDetector
    return await TrendDetector.get_trending_report()
