from uuid import UUID
from pydantic import BaseModel


class ModelInfo(BaseModel):
    id: UUID
    display_name: str
    model_name: str