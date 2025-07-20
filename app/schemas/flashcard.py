from pydantic import BaseModel, Field, ValidationError
from typing import List, Literal

class Flashcard(BaseModel):
    id: str
    question: str
    answer: str
    difficulty: Literal[1, 2, 3, 4, 5]
    topic: str
