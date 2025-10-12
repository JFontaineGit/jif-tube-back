from fastapi import HTTPException, status
from sqlmodel import Session
from typing import Optional, Dict
from datetime import datetime, timezone
from app.repositories.users import UsersRepository
from app.repositories.cache import CacheRepository
from app.core.security import jwt_handler, hash_password, verify_password
from app.schemas.users import UserCreate, UserRead, Token
from app.models import User
from app.core.config import settings

class AuthService:
    """Service para autenticación y autorización."""
    
    def __init__(self, session: Session):
        self.session = session
        self.users_repo = UsersRepository(session)
        self.cache_repo = CacheRepository(session)
        self.jwt = jwt_handler

    def register(self, user_data: UserCreate) -> UserRead:
        """Registra user: valida uniqueness, hash password, crea."""
        # Check unique email
        if self.users_repo.get_by_email(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        
        # Check unique username
        if self.users_repo.get_by_username(user_data.username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken"
            )
        
        # Hash y create
        user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=hash_password(user_data.password),
            role="user",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        created = self.users_repo.create(user)
        self.session.commit()
        
        return UserRead.model_validate(created)

    def authenticate(self, username_or_email: str, password: str) -> Token:
        """Login: verifica creds, genera tokens."""
        # Buscar usuario
        user = (
            self.users_repo.get_by_email(username_or_email) or 
            self.users_repo.get_by_username(username_or_email)
        )
        
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username/email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user"
            )
        
        # Generar tokens usando la clase
        access = self.jwt.create_access_token(
            user.username,
            user.id,  # ✅ Pasa user_id
            [user.role]
        )
        refresh = self.jwt.create_refresh_token(user.username, user.id)
        
        return Token(
            access_token=access,
            refresh_token=refresh,
            token_type="bearer",
            expires_in=self.jwt.access_token_expire_minutes * 60
        )

    def refresh_tokens(self, refresh_token: str) -> Token:
        """Rota tokens: verifica refresh, genera nuevos."""
        # Verificar token con blacklist check
        payload = self.jwt.verify_token(
            refresh_token,
            expected_type="refresh",
            check_blacklist_fn=self._is_blacklisted 
        )
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        username = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Verificar usuario
        user = self.users_repo.get_by_username(username)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not found or inactive"
            )
        
        # Blacklistear el refresh viejo
        self._blacklist_token(refresh_token, "refresh")
        
        # Generar nuevos
        new_access = self.jwt.create_access_token(
            username,
            payload.get("user_id"),  # ✅ Usa user_id del token
            [user.role]
        )
        new_refresh = self.jwt.create_refresh_token(username, payload.get("user_id"))
    
        return Token(
            access_token=new_access,
            refresh_token=new_refresh,
            token_type="bearer",
            expires_in=self.jwt.access_token_expire_minutes * 60
        )

    def logout(self, refresh_token: str) -> None:
        """Revoca refresh token: blacklistea en cache."""
        payload = self.jwt.verify_token(
            refresh_token,
            expected_type="refresh",
            check_blacklist_fn=self._is_blacklisted
        )
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        self._blacklist_token(refresh_token, "refresh")

    def verify_access_token(self, access_token: str) -> Dict:
        """Verifica access token (para dependency en routes)."""
        payload = self.jwt.verify_token(
            access_token,
            expected_type="access",
            check_blacklist_fn=self._is_blacklisted
        )
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return payload

    def _blacklist_token(self, token: str, token_type: str) -> None:
        """Agrega token a blacklist."""
        jti = self.jwt.extract_jti(token)
        if not jti:
            return
        
        ttl_minutes = self.jwt.get_token_ttl_minutes(token_type) + 60  # +1h buffer
        blacklist_key = f"blacklist:{jti}"
        
        self.cache_repo.set(blacklist_key, {"revoked": True}, ttl_minutes=ttl_minutes)
        self.session.commit()

    def _is_blacklisted(self, jti: str) -> bool:
        """Chequea si JTI está en blacklist."""
        blacklist_key = f"blacklist:{jti}"
        return self.cache_repo.get(blacklist_key) is not None