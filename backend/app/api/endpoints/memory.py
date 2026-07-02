from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# Simple in‑memory store (volatile, for demo purposes)
_memory_store: dict[str, str] = {}

class MemoryItem(BaseModel):
    value: str

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
