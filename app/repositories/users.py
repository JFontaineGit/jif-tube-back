from sqlmodel import select, Session
from typing import Optional, List
from uuid import UUID
from app.models import User

class UsersRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, user: User) -> User:
        """Crea un user (password ya hasheado en service)."""
        self.session.add(user)
        self.session.flush()  # Para obtener el ID sin commitear
        self.session.refresh(user)
        return user

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Obtiene por ID."""
        return self.session.get(User, user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        """Obtiene por email (para login/uniqueness)."""
        statement = select(User).where(User.email == email)
        return self.session.exec(statement).first()

    def get_by_username(self, username: str) -> Optional[User]:
        """Obtiene por username (para auth)."""
        statement = select(User).where(User.username == username)
        return self.session.exec(statement).first()

    def update(self, user: User) -> User:
        """Actualiza fields (e.g., updated_at auto en service)."""
        self.session.add(user)
        self.session.flush()
        self.session.refresh(user)
        return user

    def delete(self, user_id: UUID) -> bool:
        """Borra user (cascade a history/library)."""
        user = self.get_by_id(user_id)
        if user:
            self.session.delete(user)
            self.session.flush()
            return True
        return False

    def get_multi(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Lista users con paginación."""
        statement = select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
        return list(self.session.exec(statement).all())