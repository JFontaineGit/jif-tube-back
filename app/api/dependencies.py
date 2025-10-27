from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session
from typing import Any, Dict, Optional
from uuid import UUID
from app.db.session import get_db
from app.repositories.users import UsersRepository
from app.services.auth_service import AuthService
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def require_bearer_token(token: str = Depends(oauth2_scheme)) -> str:
    """Ensure that a Bearer token is present and return it."""
    if not token:
        raise _bearer_exception(
            "Missing or invalid access token. Include Authorization: Bearer <token>"
        )
    return token


def get_current_user(
    token: str = Depends(require_bearer_token),
    db: Session = Depends(get_db)
) -> User:
    """Return the authenticated user associated with the given access token."""
    service = AuthService(db)

    try:
        payload = service.verify_access_token(token)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            raise _bearer_exception(exc.detail or "Could not validate credentials") from exc
        raise

    return _load_user_from_payload(db, payload)


def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Optional auth dependency. Returns the user or ``None`` if missing/invalid."""
    if not token:
        return None

    service = AuthService(db)

    try:
        payload = service.verify_access_token(token)
        user = _load_user_from_payload(db, payload)
    except HTTPException:
        return None

    if not user.is_active:
        return None

    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Return the authenticated user ensuring it is active."""
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require that the current user has administrative privileges."""
    if current_user.role not in {"admin", "superuser"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def get_user_id(current_user: User = Depends(get_current_user)) -> UUID:
    """Helper dependency: extract the user's UUID from the authenticated user."""
    return current_user.id


def _load_user_from_payload(db: Session, payload: Dict[str, Any]) -> User:
    """Resolve a user instance from the decoded JWT payload."""
    user_id_raw = payload.get("user_id") or payload.get("sub")
    if not user_id_raw:
        raise _bearer_exception("Invalid token payload: missing user_id")

    try:
        user_uuid = UUID(str(user_id_raw))
    except (TypeError, ValueError) as err:
        raise _bearer_exception("Invalid token: malformed user_id") from err

    user = UsersRepository(db).get_by_id(user_uuid)
    if not user:
        raise _bearer_exception("User not found")

    return user


def _bearer_exception(detail: str) -> HTTPException:
    """Create a standardized 401 response for bearer authentication errors."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
