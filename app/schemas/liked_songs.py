from pydantic import BaseModel, field_validator
from typing import Optional
from uuid import UUID
from datetime import datetime
from .songs import SongRead


class LikedSongCreate(BaseModel):
    song_id: str

    @field_validator('song_id')
    @classmethod
    def validate_song_id(cls, v: str) -> str:
        if not v or len(v) != 11:
            raise ValueError('Invalid YouTube video ID')
        return v


class LikedSongRead(BaseModel):
    id: UUID
    user_id: UUID
    song_id: str
    liked_at: datetime
    song: Optional[SongRead] = None

    model_config = {"from_attributes": True}
