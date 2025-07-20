from pydantic import BaseModel, Field, ValidationError
from typing import List, Literal, Optional

class QuizQuestion(BaseModel):
    id: str
    question: str
    options: Optional[List[str]] = Field(default=[])
    correct_answer: str
    explanation: str
    difficulty: Literal[1, 2, 3]
    topic: str
    question_type: Literal["multiple_choice", "true_false", "short_answer"]