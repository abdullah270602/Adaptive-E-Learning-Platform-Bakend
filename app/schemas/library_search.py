from pydantic import BaseModel, Field
from typing import List, Optional

class LibrarySearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500, description="Search query")

class DocumentReference(BaseModel):
    id: str
    title: str
    topic: str
    type: str

class LibrarySearchResponse(BaseModel):
    answer: str
    sources: List[str]
    references: List[DocumentReference]
