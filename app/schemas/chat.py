from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

class ChatMessageCreate(BaseModel):
    chat_session_id: UUID
    document_id: UUID
    document_type: str
    content: str
    model_id: Optional[UUID] = Field(default=None)
    current_page: Optional[int] = None
    section_id: Optional[UUID] = None
    chapter_id: Optional[UUID] = None

