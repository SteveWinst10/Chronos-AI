from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_timeline():
    """Placeholder timeline endpoint returning dummy timeline data."""
    return {"timeline": []}
