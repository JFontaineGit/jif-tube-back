from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session
from typing import List
from uuid import UUID
from app.db.session import get_db
from app.repositories.users import UsersRepository
from app.schemas.users import UserRead
from app.api.dependencies import require_admin, get_current_user
from app.models import User

router = APIRouter(prefix="/users", tags=["Users"])


# Nota: utilizamos respuestas explícitas para dejar claro en el esquema OpenAPI
# que estos endpoints requieren autenticación vía Bearer token.


@router.get(
    "/me",
    response_model=UserRead,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid access token"},
    },
)
def read_current_user(current_user: User = Depends(get_current_user)):
    """Obtiene el perfil del usuario autenticado."""
    return UserRead.model_validate(current_user)


@router.get(
    "/",
    response_model=List[UserRead],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid access token"},
        status.HTTP_403_FORBIDDEN: {"description": "Admin access required"},
    },
)
def list_users(
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=500, description="Cantidad máxima de resultados"),
    _admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Lista todos los usuarios (solo admin).
    
    Paginación con skip/limit.
    """
    users = UsersRepository(db).get_multi(skip=skip, limit=limit)
    return [UserRead.model_validate(u) for u in users]