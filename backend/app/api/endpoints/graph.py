from fastapi import APIRouter

router = APIRouter()

@router.get("/graph")
async def graph_snapshot():
    """Placeholder graph endpoint returning static nodes and edges."""
    return {
        "nodes": [
            {"id": 1, "label": "Node1"},
            {"id": 2, "label": "Node2"}
        ],
        "edges": [
            {"source": 1, "target": 2, "type": "directed"}
        ]
    }
