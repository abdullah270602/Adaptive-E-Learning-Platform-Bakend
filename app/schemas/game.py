
from pydantic import BaseModel


class GameRequest(BaseModel):
    content: str
