from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

class DocumentProgressUpdate(BaseModel):
    document_id: UUID = Field(..., example="10273a10-b1ea-4514-b6c7-d1bf2d20a856")
    document_type: str = Field(..., example="book")
    page_number: Optional[int] = Field(None, example=42)
    section_id: Optional[UUID] = Field(None, example="d945fa7c-2d8d-4302-811c-05a7ab9646dc, Can be null as well")
    chapter_id: Optional[UUID] = Field(None, example="10273a10-b1ea-4514-b6c7-d1bf2d20a856 Can be null as well")