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
    
    Retorna access token (15 min) y refresh token (7 días).
    
    - **username**: Username o email
    - **password**: Password del usuario
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
    
    El refresh token viejo se invalida (forward secrecy).
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
    
    El access token seguirá válido hasta que expire (15 min).
    """
    service = AuthService(db)
    service.logout(refresh_token)
    return None  # 204 No Content