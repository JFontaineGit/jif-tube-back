from sqlmodel import Session
from typing import Optional
from app.models import Song
from app.schemas.songs import SongCreate

class SongsRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_or_create_from_youtube_meta(self, song_data: SongCreate) -> Song:
        """Upsert: Crea o recupera song por video_id."""
        existing = self.get_by_id(song_data.id)
        if existing:
            return existing
        
        # Crea nuevo
        new_song = Song(**song_data.model_dump())
        self.session.add(new_song)
        self.session.flush()
        self.session.refresh(new_song)
        return new_song

    def get_by_id(self, song_id: str) -> Optional[Song]:
        """Obtiene por YT video_id."""
        return self.session.get(Song, song_id)