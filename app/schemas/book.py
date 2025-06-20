from uuid import UUID
from pydantic import BaseModel, UUID, Field
from datetime import datetime
from typing import List


class SectionModel(BaseModel):
    id: UUID
    chapter_id: UUID
    title: str = Field(..., min_length=1)
    page: int
    s3_key: str = Field(..., min_length=1)
    embedding_id: str = None
    added_date: datetime


class ChapterModel(BaseModel):
    id: UUID
    book_id: UUID
    chapter_number: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    created_at: datetime
    sections: List[SectionModel] = []


class BookModel(BaseModel):
    id: UUID
    user_id: UUID
    title: str = Field(..., min_length=1)
    file_name: str = Field(..., min_length=1)
    file_id: str = Field(..., min_length=1)
    s3_key: str = Field(..., min_length=1)
    created_at: datetime
    chapters: List[ChapterModel] = []


class BookSchema(BaseModel):
    id: UUID
    title: str
    file_name: str
    file_id: str
    s3_key: str
    created_at: datetime

    class Config:
        orm_mode = True


class BookListResponse(BaseModel):
    books: List[BookSchema]
