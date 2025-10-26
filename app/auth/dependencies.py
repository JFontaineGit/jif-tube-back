from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session
from uuid import UUID
import jwt
from jwt import PyJWTError

from app.db import SessionDep, get_db
from app.models import User

# Configuración JWT (misma que en auth.py)
SECRET_KEY = "6e4486e782d27b01c63ce61fa2ad197df535f3f1f2fa91a128d6f2ac71772576"
ALGORITHM = "HS256"

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_db)
) -> User:
    """Obtiene el usuario actual basado en el token JWT"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Verificar que es un token de acceso
        if payload.get("type") != "access":
            raise credentials_exception
            
        user_id_raw = payload.get("sub")
        if user_id_raw is None:
            raise credentials_exception

        try:
            user_uuid = UUID(str(user_id_raw))
        except ValueError:
            raise credentials_exception

    except PyJWTError:
        raise credentials_exception

    # Buscar usuario en la base de datos
    user = session.get(User, user_uuid)
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Obtiene el usuario actual y verifica que esté activo"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user