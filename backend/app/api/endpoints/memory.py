from fastapi import APIRouter

router = APIRouter()

@router.get("/memory")
async def memory_status():
    """Placeholder memory endpoint returning empty status."""
    return {"status": "memory endpoint placeholder"}
