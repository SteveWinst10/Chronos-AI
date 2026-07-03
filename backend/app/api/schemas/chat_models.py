# app/api/schemas/chat_models.py
from pydantic import BaseModel, Field
from typing import List, Optional

class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the message sender: 'user' or 'assistant'")
    content: str = Field(..., description="The text content of the message")

class ChatRequest(BaseModel):
    message: str = Field(..., description="The prompt or question sent to the assistant")
    history: Optional[List[ChatMessage]] = Field(default=[], description="Previous conversational history log")

class ChatResponse(BaseModel):
    status: str
    response: str = Field(..., description="The generated response from the assistant agent")