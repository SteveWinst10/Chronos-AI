from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Simple in‑memory store (volatile, for demo purposes)
_memory_store: dict[str, str] = {}

class MemoryItem(BaseModel):
    value: str


@router.get("/vector")
async def get_vector_memories():
    try:
        from app.storage.vector_db import get_vector_db
        db = get_vector_db()
        if "memories" not in db.table_names():
            return {"memories": []}
        
        table = db.open_table("memories")
        df = table.to_pandas()
        memories = []
        for _, row in df.iterrows():
            metadata_str = row["metadata"]
            try:
                metadata = json.loads(metadata_str)
            except Exception:
                metadata = {"raw_text": metadata_str}
            
            memories.append({
                "id": row["id"],
                "raw_text": metadata.get("raw_text", ""),
                "conversation_id": metadata.get("conversation_id", "default"),
            })
        return {"memories": memories}
    except Exception as e:
        logger.exception("Failed to fetch vector memories")
        raise HTTPException(status_code=500, detail=f"Failed to fetch vector memories: {e}")


@router.delete("/cognee/{entity_id}")
async def delete_cognee_memory(entity_id: str):
    try:
        from app.services.cognee.memory_manager import CogneeMemoryManager
        success = await CogneeMemoryManager.purge_node_memory(entity_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to fully purge memory.")
        return {"status": "success", "purged": entity_id}
    except Exception as e:
        logger.exception("Failed to purge Cognee memory")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{key}")
async def get_item(key: str):
    if key not in _memory_store:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"key": key, "value": _memory_store[key]}

@router.post("/{key}")
async def set_item(key: str, item: MemoryItem):
    _memory_store[key] = item.value
    return {"status": "saved", "key": key}

@router.delete("/{key}")
async def delete_item(key: str):
    _memory_store.pop(key, None)
    return {"status": "deleted", "key": key}
