from pydantic import BaseModel, Field
from typing import List, Literal, Annotated
from uuid import UUID


class RatingAnswer(BaseModel):
    question: str
    style: Literal["Visual", "ReadingWriting", "Kinesthetic"]
    score: Annotated[int, Field(ge=1, le=5)]

class MCQAnswer(BaseModel):
    question: str
    answer: str

class LearningProfileSubmission(BaseModel):
    ratings: List[RatingAnswer]
    mcqs: List[MCQAnswer]

class LearningProfileResponse(BaseModel):
    user_id: UUID
    visual_score: float
    reading_score: float
    kinesthetic_score: float
    primary_style: str