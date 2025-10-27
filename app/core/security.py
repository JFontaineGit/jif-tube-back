from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID
from jose import jwt, JWTError
from app.core.config import settings
from app.models import pwd_context
import uuid

def hash_password(password: str) -> str:
    """Hash con bcrypt/argon2."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed: str) -> bool:
    """Verifica contra hash."""
    return pwd_context.verify(plain_password, hashed)

class JWTHandler:
    """Manejador de JWT con soporte para blacklist."""
    
    def __init__(
        self,
        secret_key: str = None,
        algorithm: str = None,
        access_token_expire_minutes: int = None,
        refresh_token_expire_days: int = None
    ):
        """
        Inicializa handler con config (usa defaults de settings si no se pasa).
        
        Args:
            secret_key: Clave secreta para firmar tokens
            algorithm: Algoritmo JWT (default: HS256)
            access_token_expire_minutes: TTL de access tokens
            refresh_token_expire_days: TTL de refresh tokens
        """
        self.secret_key = secret_key or settings.SECRET_KEY
        self.algorithm = algorithm or settings.JWT_ALGORITHM
        self.access_token_expire_minutes = (
            access_token_expire_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        self.refresh_token_expire_days = (
            refresh_token_expire_days or settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    
    def create_access_token(
        self,
        user_id: UUID,
        username: str,
        scopes: Optional[List[str]] = None,
    ) -> str:
        """Crea un access token firmado.

        Args:
            user_id: Identificador del usuario (UUID).
            username: Username del usuario (útil para auditoría/UI).
            scopes: Lista de roles/permisos opcionales.
        """
        if scopes is None:
            scopes = []
        
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "sub": str(user_id),
            "user_id": str(user_id),
            "username": username,
            "scopes": scopes,
            "exp": expire,
            "iat": now,
            "jti": str(uuid.uuid4()),
            "type": "access"
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(
        self,
        user_id: UUID,
        username: str,
        scopes: Optional[List[str]] = None,
    ) -> str:
        """Crea un refresh token con claims alineadas al access token."""
        if scopes is None:
            scopes = []

        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self.refresh_token_expire_days)

        payload = {
            "sub": str(user_id),
            "user_id": str(user_id),
            "username": username,
            "scopes": scopes,
            "exp": expire,
            "iat": now,
            "jti": str(uuid.uuid4()),
            "type": "refresh"
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decodifica y valida token.
        
        Args:
            token: Token JWT
            
        Returns:
            Payload del token o None si inválido
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except JWTError:
            return None
    
    def verify_token(
        self,
        token: str,
        expected_type: str,
        check_blacklist_fn: Optional[callable] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Verifica token completo (decodifica + valida tipo + blacklist).
        
        Args:
            token: Token JWT
            expected_type: "access" o "refresh"
            check_blacklist_fn: Función para verificar blacklist (recibe JTI)
            
        Returns:
            Payload si válido, None si inválido
        """
        # Decodificar
        payload = self.decode_token(token)
        if not payload:
            return None
        
        # Verificar tipo
        token_type = payload.get("type")
        if token_type != expected_type:
            return None
        
        # Verificar blacklist (si se provee función)
        if check_blacklist_fn:
            jti = payload.get("jti")
            if jti and check_blacklist_fn(jti):
                return None
        
        return payload
    
    def extract_jti(self, token: str) -> Optional[str]:
        """
        Extrae JTI del token sin validar expiración.
        
        Args:
            token: Token JWT
            
        Returns:
            JTI o None
        """
        try:
            # Decodifica sin verificar expiración
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )
            return payload.get("jti")
        except JWTError:
            return None
    
    def get_token_ttl_minutes(self, token_type: str) -> int:
        """
        Obtiene TTL en minutos según tipo de token.
        
        Args:
            token_type: "access" o "refresh"
            
        Returns:
            TTL en minutos
        """
        if token_type == "access":
            return self.access_token_expire_minutes
        elif token_type == "refresh":
            return self.refresh_token_expire_days * 24 * 60
        return 0

jwt_handler = JWTHandler()