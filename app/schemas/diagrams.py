from typing import List, Optional
from pydantic import BaseModel


class DiagramRequest(BaseModel):
    content: str
    summary: Optional[str] = None

class DiagramResponse(BaseModel):
    diagrams: List[str]
