from sqlmodel import delete, Session
from typing import Optional, Dict
from app.models import CacheEntry
from sqlalchemy.dialects.postgresql import insert
import time

class CacheRepository:
    def __init__(self, session: Session):
        self.session = session

    def set(self, key: str, data: Dict, ttl_minutes: int = 60) -> None:
        """Setea cache con UPSERT (reemplaza si existe)."""
        timestamp_ms = int(time.time() * 1000)
        
        # UPSERT para Postgres
        stmt = insert(CacheEntry).values(
            cache_key=key,
            data=data,
            timestamp=timestamp_ms,
            ttl_minutes=ttl_minutes
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=['cache_key'],
            set_=dict(
                data=data,
                timestamp=timestamp_ms,
                ttl_minutes=ttl_minutes
            )
        )
        self.session.exec(stmt)
        self.session.flush()

    def get(self, key: str) -> Optional[Dict]:
        """Obtiene si no expirado (check TTL)."""
        entry = self.session.get(CacheEntry, key)
        if not entry:
            return None
        
        now_ms = int(time.time() * 1000)
        expire_ms = entry.timestamp + (entry.ttl_minutes * 60 * 1000)
        
        if now_ms > expire_ms:
            self.invalidate(key)
            return None
        
        return entry.data

    def invalidate(self, key: str) -> None:
        """Borra entry específica."""
        stmt = delete(CacheEntry).where(CacheEntry.cache_key == key)
        self.session.exec(stmt)
        self.session.flush()

    def invalidate_all(self) -> None:
        """Limpia todo cache (e.g., on deploy)."""
        stmt = delete(CacheEntry)
        self.session.exec(stmt)
        self.session.flush()