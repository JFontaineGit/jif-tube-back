from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session
from typing import List
from app.db.session import get_db
from app.repositories.users import UsersRepository
from app.schemas.users import UserRead
from app.api.dependencies import require_admin, get_user_id

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserRead)
def read_current_user(
    user_id: int = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    """
    Obtiene el perfil del usuario actual.
    
    Requiere autenticación.
    """
    user = UsersRepository(db).get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return UserRead.model_validate(user)


@router.get("/", response_model=List[UserRead])
def list_users(
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=500, description="Cantidad máxima de resultados"),
    admin: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Lista todos los usuarios (solo admin).
    
    Paginación con skip/limit.
    """
    users = UsersRepository(db).get_multi(skip=skip, limit=limit)
    return [UserRead.model_validate(u) for u in users]