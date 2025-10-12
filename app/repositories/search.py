from sqlmodel import select, Session
from typing import List, Optional
from app.models import SearchHistory
import time

class SearchRepository:
    def __init__(self, session: Session):
        self.session = session

    def log_search(self, user_id: int, query: str, timestamp: Optional[int] = None) -> SearchHistory:
        """Loggea búsqueda; incrementa count si existe."""
        if timestamp is None:
            timestamp = int(time.time() * 1000)
        
        statement = select(SearchHistory).where(
            SearchHistory.user_id == user_id,
            SearchHistory.query == query
        )
        existing = self.session.exec(statement).first()
        
        if existing:
            existing.count += 1
            existing.timestamp = timestamp  # Update to latest
            self.session.add(existing)
            self.session.flush()
            self.session.refresh(existing)
            return existing
        
        # Nueva entrada
        new_search = SearchHistory(
            query=query,
            timestamp=timestamp,
            count=1,
            user_id=user_id
        )
        self.session.add(new_search)
        self.session.flush()
        self.session.refresh(new_search)
        return new_search

    def get_history_by_user(self, user_id: int, limit: int = 10) -> List[SearchHistory]:
        """Lista reciente por user, ordenada por timestamp DESC."""
        statement = (
            select(SearchHistory)
            .where(SearchHistory.user_id == user_id)
            .order_by(SearchHistory.timestamp.desc())
            .limit(limit)
        )
        return list(self.session.exec(statement).all())