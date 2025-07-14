from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal, Optional
from uuid import UUID

from app.services.constants import DEFAULT_MODEL_ID

class ChatMessageCreate(BaseModel):
    chat_session_id: UUID
    document_id: UUID
    document_type: str
    content: str
    current_page: int
    model_id: Optional[UUID] = DEFAULT_MODEL_ID
    section_name: Optional[str] = None
    chapter_name: Optional[str] = None

class ChatMessageResponse(BaseModel):
    chat_session_id: UUID
    user_id: UUID
    role: Literal["user", "assistant"]
    content: str
    model_id: Optional[UUID]
    tool_type: Optional[str] = None
    tool_response_id: Optional[UUID] = None
    created_at: datetime