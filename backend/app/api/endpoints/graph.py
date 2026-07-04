from fastapi import APIRouter
from app.storage.neo4j_graph import neo4j_graph

router = APIRouter()

@router.get("/")
async def graph_snapshot():
    """Returns actual Neo4j graph nodes and edges."""
    nodes = neo4j_graph.get_all_nodes()
    edges = neo4j_graph.get_all_edges()
    return {
        "nodes": nodes,
        "edges": edges
    }
