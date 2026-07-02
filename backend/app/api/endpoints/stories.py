from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_stories():
    """Placeholder stories endpoint returning dummy list of stories."""
    return {"stories": []}
