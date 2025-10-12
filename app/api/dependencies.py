from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer
from sqlmodel import Session
from typing import Optional, Dict
from app.db.session import get_db
from app.services.auth_service import AuthService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
http_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Dependency: Verifica access token y retorna payload.
    
    Raises:
        HTTPException 401 si token inválido
        
    Returns:
        Payload con: sub (username), user_id, scopes
    """
    service = AuthService(db)
    
    try:
        payload = service.verify_access_token(token)
        return payload
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_optional(
    credentials = Depends(http_bearer),
    db: Session = Depends(get_db)
) -> Optional[Dict]:
    """
    Dependency: Auth opcional (no falla si no hay token).
    
    Returns:
        Payload si token válido, None si no hay token o es inválido
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    service = AuthService(db)
    
    try:
        payload = service.verify_access_token(token)
        return payload
    except:
        return None  # No falla, solo retorna None


def get_current_active_user(
    current_user: Dict = Depends(get_current_user)
) -> Dict:
    """
    Extiende get_current_user para verificar que el user esté activo.
    
    En el futuro podés agregar:
    - Verificación de email
    - Verificación de banned status
    - Etc.
    """
    # Si necesitás verificar is_active desde DB:
    # user = UsersRepository(db).get_by_id(current_user["user_id"])
    # if not user.is_active:
    #     raise HTTPException(403, "Inactive user")
    
    return current_user


def require_admin(
    current_user: Dict = Depends(get_current_user)
) -> Dict:
    """
    Dependency: Requiere rol admin.
    
    Raises:
        HTTPException 403 si no es admin
    """
    scopes = current_user.get("scopes", [])
    
    # Validar que scopes sea lista
    if not isinstance(scopes, list):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid token scopes format"
        )
    
    if "admin" not in scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user


def get_user_id(current_user: Dict = Depends(get_current_user)) -> int:
    """
    Helper dependency: Extrae solo el user_id del token.
    
    Útil para endpoints que solo necesitan el ID.
    """
    user_id = current_user.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid token: missing user_id"
        )
    return int(user_id)