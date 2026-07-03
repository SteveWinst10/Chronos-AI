import logging

from fastapi import APIRouter, HTTPException

from app.api.schemas.chat_models import ChatRequest, ChatResponse
from app.services.cognee.memory_manager import CogneeMemoryManager
from app.services.llm.llm_client import LLMClient
from app.services.llm.prompts import CONTEXT_ENGINE_PROMPT
from app.services.retrieval.context_builder import build_context

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def process_chat_message(payload: ChatRequest):
    try:
        user_message = payload.message.strip()
        if not user_message:
            raise HTTPException(status_code=400, detail="Message content cannot be blank.")

        conversation_id = _derive_conversation_id(payload)

        await CogneeMemoryManager.remember_context(user_message, conversation_id)

        recall_data = await CogneeMemoryManager.recall_context(user_message)

        context = build_context(user_message, recall_data)

        llm = LLMClient()
        response = await llm.get_completion(context, CONTEXT_ENGINE_PROMPT)

        await CogneeMemoryManager.remember_context(response, conversation_id)

        return ChatResponse(status="success", response=response)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Chat processing failed")
        raise HTTPException(status_code=500, detail=str(e))


def _derive_conversation_id(payload: ChatRequest) -> str:
    if not payload.history:
        return "default"
    content_concat = "".join(m.content for m in payload.history)
    return f"conv_{abs(hash(content_concat))}"
