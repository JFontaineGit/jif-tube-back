from pydantic import BaseModel, field_validator
from typing import Optional
from uuid import UUID
from .songs import SongRead

class SearchCreate(BaseModel):
    query: str
    timestamp: Optional[int] = None
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Query cannot be empty')
        if len(v) > 500:
            raise ValueError('Query too long (max 500 chars)')
        return v

class SearchRead(BaseModel):
    id: UUID
    query: str
    timestamp: int
    count: int
    user_id: UUID
    
    model_config = {"from_attributes": True}
    
class SongSearchResult(SongRead):
    """Song con metadata de búsqueda (score, ranking)."""
    custom_score: float = 0.0
    rank: Optional[int] = None