# app/api/endpoints/chat.py
from fastapi import APIRouter, HTTPException
from app.api.schemas.chat_models import ChatRequest, ChatResponse

router = APIRouter()

@router.post("/", response_model=ChatResponse)
async def process_chat_message(payload: ChatRequest):
    """
    POST endpoint to handle user prompts and chat history logs.
    Validates input using Pydantic contracts.
    """
    try:
        user_message = payload.message.strip()
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Message content cannot be blank.")
            
        # Standard structural mock response until Person 4 hooks up the real LLM service engine
        mock_ai_reply = f"Hello! I am Chronos-AI. You asked: '{user_message}'. I can see your conversation history has {len(payload.history)} previous messages."
        
        return {
            "status": "success",
            "response": mock_ai_reply
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))