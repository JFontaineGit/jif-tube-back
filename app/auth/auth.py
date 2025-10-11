from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import select, Session
from datetime import datetime, timedelta
from typing import Optional
import jwt
from jwt import PyJWTError

from app.db import SessionDep
from app.models import User, UserCreate, UserLogin, UserResponse, Token, PasswordError

# Configuración JWT
SECRET_KEY = "6e4486e782d27b01c63ce61fa2ad197df535f3f1f2fa91a128d6f2ac71772576"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 días

security = HTTPBearer()

auth_router = APIRouter(prefix="/api/auth", tags=["authentication"])

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Crea un token de acceso JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "iss": "Jif-Tube-API/0.1.0",
        "type": "access"
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    """Crea un token de refresco JWT"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "iss": "Jif-Tube-API/0.1.0",
        "type": "refresh"
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> dict:
    """Verifica y decodifica un token JWT"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_user_by_username_or_email(session: Session, username_or_email: str) -> Optional[User]:
    """Busca un usuario por username o email"""
    user = session.exec(
        select(User).where(
            (User.username == username_or_email) | (User.email == username_or_email)
        )
    ).first()
    return user

def authenticate_user(session: Session, username_or_email: str, password: str) -> Optional[User]:
    """Autentica un usuario con username/email y contraseña"""
    user = get_user_by_username_or_email(session, username_or_email)
    if not user or not user.check_password(password):
        return None
    return user

@auth_router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, session: SessionDep):
    """Registra un nuevo usuario"""
    # Verificar si el usuario ya existe
    existing_user = session.exec(
        select(User).where(
            (User.username == user_data.username) | (User.email == user_data.email)
        )
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    # Crear nuevo usuario
    try:
        user = User(
            username=user_data.username,
            email=user_data.email
        )
        user.set_password(user_data.password)
        
        session.add(user)
        session.commit()
        session.refresh(user)
        
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
    except PasswordError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password validation error: {e.message}"
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user"
        )

@auth_router.post("/login", response_model=Token)
async def login(login_data: UserLogin, session: SessionDep):
    """Autentica un usuario y devuelve tokens JWT"""
    user = authenticate_user(session, login_data.username_or_email, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Crear tokens
    access_token = create_access_token(data={"sub": str(user.id), "username": user.username})
    refresh_token = create_refresh_token(data={"sub": str(user.id), "username": user.username})
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )

@auth_router.post("/refresh", response_model=Token)
async def refresh_token(session: SessionDep, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Renueva el token de acceso usando el refresh token"""
    token = credentials.credentials
    
    try:
        payload = verify_token(token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        username = payload.get("username")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Verificar que el usuario existe y está activo
        user = session.get(User, int(user_id))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Crear nuevos tokens
        access_token = create_access_token(data={"sub": str(user.id), "username": user.username})
        refresh_token = create_refresh_token(data={"sub": str(user.id), "username": user.username})
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )
    
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

@auth_router.post("/logout")
async def logout():
    """Cierra la sesión del usuario (en el cliente se debe eliminar el token)"""
    return {"message": "Successfully logged out"}

@auth_router.get("/me", response_model=UserResponse)
async def get_current_user_info(session: SessionDep, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Obtiene información del usuario actual"""
    token = credentials.credentials
    
    try:
        payload = verify_token(token)
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user = session.get(User, int(user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
    
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )