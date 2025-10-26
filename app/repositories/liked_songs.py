from sqlmodel import select, Session
from typing import List, Optional
from uuid import UUID
from app.models import LikedSong


class LikedSongsRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, user_id: UUID, song_id: str) -> LikedSong:
        """Agrega una canción a la lista de likes (idempotente)."""
        existing = self.get_entry(user_id, song_id)
        if existing:
            return existing

        new_entry = LikedSong(user_id=user_id, song_id=song_id)
        self.session.add(new_entry)
        self.session.flush()
        self.session.refresh(new_entry)
        return new_entry

    def remove(self, user_id: UUID, song_id: str) -> bool:
        """Elimina un like."""
        entry = self.get_entry(user_id, song_id)
        if entry:
            self.session.delete(entry)
            self.session.flush()
            return True
        return False

    def get_entry(self, user_id: UUID, song_id: str) -> Optional[LikedSong]:
        """Obtiene un like específico."""
        statement = select(LikedSong).where(
            LikedSong.user_id == user_id,
            LikedSong.song_id == song_id
        )
        return self.session.exec(statement).first()

    def list_by_user(self, user_id: UUID) -> List[LikedSong]:
        """Lista los likes del usuario ordenados por fecha."""
        statement = (
            select(LikedSong)
            .where(LikedSong.user_id == user_id)
            .order_by(LikedSong.liked_at.desc())
        )
        return list(self.session.exec(statement).all())
