from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
from .songs import SongRead

class LibraryItemCreate(BaseModel):
    song_id: str  # YT video_id
    
    @field_validator('song_id')
    @classmethod
    def validate_song_id(cls, v: str) -> str:
        if not v or len(v) != 11:
            raise ValueError('Invalid YouTube video ID')
        return v

class LibraryItemRead(BaseModel):
    id: int
    user_id: int
    song_id: str
    added_at: datetime
    song: Optional[SongRead] = None
    
    model_config = {"from_attributes": True}