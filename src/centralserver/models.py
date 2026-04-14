from typing import Any
from pydantic import BaseModel

class Song(BaseModel):
    id: str
    properties: dict[str, Any]

class SongHash(BaseModel):
    id: str
    hash: str