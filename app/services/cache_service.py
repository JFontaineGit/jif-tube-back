from typing import Optional, Dict, Any
from sqlmodel import Session, select, delete
from app.repositories.cache import CacheRepository
from app.models import CacheEntry
import time

class CacheService:
    """Wrapper sobre CacheRepository con helpers adicionales."""
    
    def __init__(self, session: Session):
        self.session = session
        self.repo = CacheRepository(session)

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene data si no expirada (TTL check interno en repo).
        
        Returns:
            Data del cache o None si expirado/no existe
        """
        return self.repo.get(key)

    def set(self, key: str, data: Dict[str, Any], ttl_minutes: int = 60) -> None:
        """
        Setea cache con TTL.
        
        Args:
            key: Cache key
            data: Datos a cachear (debe ser JSON-serializable)
            ttl_minutes: Tiempo de vida en minutos
        """
        self.repo.set(key, data, ttl_minutes)

    def invalidate(self, key: str) -> None:
        """Invalida una entrada específica."""
        self.repo.invalidate(key)

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalida todas las keys que matcheen un patrón.
        
        Args:
            pattern: Patrón SQL LIKE (e.g., "search:%")
            
        Returns:
            Cantidad de entradas invalidadas
        """
        stmt = delete(CacheEntry).where(CacheEntry.cache_key.like(pattern))
        result = self.session.exec(stmt)
        self.session.commit()
        return result.rowcount

    def cleanup_expired(self, batch_size: int = 100) -> int:
        """
        Purge de entradas expiradas (usa paginación para escalar).
        
        Args:
            batch_size: Cantidad de entradas a procesar por batch
            
        Returns:
            Total de entradas eliminadas
        """
        now_ms = int(time.time() * 1000)
        deleted_total = 0
        
        while True:
            # Query batch de entradas (limitado para no explotar memoria)
            stmt = select(CacheEntry).limit(batch_size)
            entries = list(self.session.exec(stmt).all())
            
            if not entries:
                break
            
            deleted_batch = 0
            for entry in entries:
                expire_ms = entry.timestamp + (entry.ttl_minutes * 60 * 1000)
                if now_ms > expire_ms:
                    self.repo.invalidate(entry.cache_key)
                    deleted_batch += 1
            
            deleted_total += deleted_batch
            
            # Si no se borró nada en este batch, terminamos
            if deleted_batch == 0:
                break
        
        self.session.commit()
        return deleted_total