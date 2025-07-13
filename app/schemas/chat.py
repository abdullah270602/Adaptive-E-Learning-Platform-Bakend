from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

class ChatMessageCreate(BaseModel):
    chat_session_id: UUID
    document_id: UUID
    document_type: str
    content: str
    current_page: int
    model_id: Optional[UUID] = Field(default=None)
    section_id: Optional[UUID] = None
    chapter_id: Optional[UUID] = None

