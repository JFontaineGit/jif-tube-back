from fastapi import APIRouter, Depends, Path, HTTPException, status
from sqlmodel import Session
from typing import Optional
from app.db.session import get_db
from app.services.youtube_service import YouTubeService
from app.schemas.songs import SongRead
from app.api.dependencies import get_current_user_optional

router = APIRouter(prefix="/songs", tags=["Songs"])


@router.get("/{video_id}", response_model=SongRead)
def get_song(
    video_id: str = Path(..., min_length=10, max_length=15, description="YouTube video ID"),
    current_user: Optional[dict] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Obtiene detalles de una canción por su video ID de YouTube.
    
    - **video_id**: ID del video de YouTube (e.g., dQw4w9WgXcQ)
    
    Auth opcional.
    """
    service = YouTubeService(db)
    
    try:
        song = service.get_video(video_id)
        if not song:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video {video_id} not found"
            )
        return song
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching video: {str(e)}"
        )