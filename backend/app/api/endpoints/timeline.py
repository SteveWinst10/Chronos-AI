from fastapi import APIRouter

router = APIRouter()

@router.get("/timeline")
async def get_timeline():
    """Placeholder timeline endpoint returning dummy timeline data."""
    return {"timeline": []}
