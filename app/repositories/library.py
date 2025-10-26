from sqlmodel import select, Session
from typing import List, Optional
from uuid import UUID
from app.models import UserLibrary

class LibraryRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, user_id: UUID, song_id: str) -> UserLibrary:
        """Agrega a library (idempotente: devuelve existente si ya está)."""
        existing = self.get_entry(user_id, song_id)
        if existing:
            return existing
        
        new_entry = UserLibrary(user_id=user_id, song_id=song_id)
        self.session.add(new_entry)
        self.session.flush()
        self.session.refresh(new_entry)
        return new_entry

    def remove(self, user_id: UUID, song_id: str) -> bool:
        """Remueve de library."""
        entry = self.get_entry(user_id, song_id)
        if entry:
            self.session.delete(entry)
            self.session.flush()
            return True
        return False

    def get_entry(self, user_id: UUID, song_id: str) -> Optional[UserLibrary]:
        """Helper para obtener entry específica."""
        statement = select(UserLibrary).where(
            UserLibrary.user_id == user_id,
            UserLibrary.song_id == song_id
        )
        return self.session.exec(statement).first()

    def list_by_user(self, user_id: UUID) -> List[UserLibrary]:
        """Lista todos por user, ordenados por fecha."""
        statement = (
            select(UserLibrary)
            .where(UserLibrary.user_id == user_id)
            .order_by(UserLibrary.added_at.desc())
        )
        return list(self.session.exec(statement).all())