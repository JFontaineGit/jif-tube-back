from fastapi import APIRouter, Depends, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session
from app.db.session import get_db
from app.services.auth_service import AuthService
from app.schemas.users import UserCreate, UserRead, Token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Registra un nuevo usuario.
    
    ✅ PÚBLICO - No requiere autenticación
    
    - **username**: Único, 3-50 caracteres
    - **email**: Email válido, único
    - **password**: Mínimo 8 caracteres, debe cumplir requisitos de seguridad
    """
    service = AuthService(db)
    return service.register(user_data)


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login con username/email + password.
    
    ✅ PÚBLICO - No requiere autenticación
    
    Retorna access token (15 min) y refresh token (7 días).
    
    - **username**: Username o email
    - **password**: Password del usuario
    
    IMPORTANTE: Este endpoint NO debe tener dependency de require_bearer_token
    porque estás OBTENIENDO el token, no validándolo.
    """
    service = AuthService(db)
    return service.authenticate(form_data.username, form_data.password)


@router.post("/refresh", response_model=Token)
def refresh(
    refresh_token: str = Form(..., description="Refresh token"),
    db: Session = Depends(get_db)
):
    """
    Renueva tokens usando refresh token.
    
    ✅ PÚBLICO - No requiere Bearer token en header (usa refresh_token en body)
    
    El refresh token viejo se invalida (forward secrecy).
    
    IMPORTANTE: NO uses require_bearer_token aquí porque el refresh_token
    va en el BODY, no en el header Authorization.
    """
    service = AuthService(db)
    return service.refresh_tokens(refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    refresh_token: str = Form(..., description="Refresh token"),
    db: Session = Depends(get_db)
):
    """
    Cierra sesión invalidando el refresh token.
    
    ✅ PÚBLICO - No requiere Bearer token en header (usa refresh_token en body)
    
    El access token seguirá válido hasta que expire (15 min).
    
    IMPORTANTE: NO uses require_bearer_token aquí porque el refresh_token
    va en el BODY, no en el header Authorization.
    """
    service = AuthService(db)
    service.logout(refresh_token)
    return None  # 204 No Content