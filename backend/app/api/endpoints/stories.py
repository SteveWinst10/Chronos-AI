from fastapi import APIRouter

router = APIRouter()

@router.get("/stories")
async def get_stories():
    """Placeholder stories endpoint returning dummy list of stories."""
    return {"stories": []}
