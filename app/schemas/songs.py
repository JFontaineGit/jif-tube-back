from pydantic import BaseModel, field_validator
from typing import Optional, Dict
from datetime import datetime

class SongBase(BaseModel):
    """Campos comunes entre Create y Read"""
    title: str
    channel_title: Optional[str] = None
    duration: Optional[str] = None
    thumbnails: Optional[Dict] = None
    published_at: Optional[datetime] = None

class SongCreate(SongBase):
    id: str  # YouTube video_id
    
    @field_validator('id')
    @classmethod
    def validate_video_id(cls, v: str) -> str:
        if not v or len(v) != 11:  # YouTube IDs son de 11 chars
            raise ValueError('Invalid YouTube video ID')
        return v
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()

class SongRead(SongBase):
    id: str
    created_at: datetime
    
    model_config = {"from_attributes": True}