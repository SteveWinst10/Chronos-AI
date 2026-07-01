from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/chat")
async def chat_stream():
    """Placeholder chat streaming endpoint.
    Returns a static list of messages for demo purposes.
    """
    return {"messages": [f"message {i}" for i in range(1, 6)]}
