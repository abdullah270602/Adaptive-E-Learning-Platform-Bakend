from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

class DocumentProgressUpdate(BaseModel):
    document_id: UUID = Field(..., )
    document_type: str = Field(..., example="book")
    page_number: Optional[int] = Field(None, example=12)
    section_id: Optional[UUID] = Field(None, example="id or Can be null as well")
    chapter_id: Optional[UUID] = Field(None, example="id or Can be null as well")