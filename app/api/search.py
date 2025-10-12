from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlmodel import Session
from typing import List, Optional
from app.db.session import get_db
from app.services.youtube_service import YouTubeService
from app.schemas.search import SongSearchResult
from app.api.dependencies import get_current_user_optional

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/", response_model=List[SongSearchResult])
def search_videos(
    q: str = Query(..., min_length=1, max_length=500, description="Término de búsqueda"),
    max_results: int = Query(10, ge=1, le=50, description="Cantidad máxima de resultados"),
    region_code: Optional[str] = Query(None, min_length=2, max_length=2, description="Código de región (e.g., AR, US)"),
    current_user: Optional[dict] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Búsqueda de canciones en YouTube.
    
    - **q**: Término de búsqueda (artista, canción, etc.)
    - **max_results**: Cantidad de resultados (1-50, default 10)
    - **region_code**: Código ISO de región (opcional)
    
    Auth opcional: Si estás autenticado, la búsqueda se loguea en tu historial.
    """
    service = YouTubeService(db)
    
    # Extraer user_id si está autenticado
    user_id = current_user.get("user_id") if current_user else None
    
    try:
        results = service.search(
            query=q,
            user_id=user_id,
            max_results=max_results,
            region_code=region_code
        )
        return results
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search error: {str(e)}"
        )