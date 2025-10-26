from fastapi import APIRouter, Depends, Path, HTTPException, status
from sqlmodel import Session
from typing import List
from app.db.session import get_db
from app.repositories.liked_songs import LikedSongsRepository
from app.repositories.songs import SongsRepository
from app.schemas.liked_songs import LikedSongCreate, LikedSongRead
from app.api.dependencies import get_user_id

router = APIRouter(prefix="/liked-songs", tags=["Liked Songs"])

AUTH_RESPONSES = {
    status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid access token"}
}


@router.post(
    "/",
    response_model=LikedSongRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        **AUTH_RESPONSES,
        status.HTTP_404_NOT_FOUND: {"description": "Song not found"},
    },
)
def like_song(
    item: LikedSongCreate,
    user_id: int = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    """Marca una canción como like.

    Requiere autenticación: Header `Authorization: Bearer <token>`.
    """
    repo = LikedSongsRepository(db)
    songs_repo = SongsRepository(db)

    song = songs_repo.get_by_id(item.song_id)
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Song {item.song_id} not found. Search it first."
        )

    entry = repo.add(user_id, item.song_id)
    db.commit()
    return LikedSongRead.model_validate(entry)


@router.delete(
    "/{song_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **AUTH_RESPONSES,
        status.HTTP_404_NOT_FOUND: {"description": "Song not found in your likes"},
    },
)
def unlike_song(
    song_id: str = Path(..., min_length=10, max_length=15, description="YouTube video ID"),
    user_id: int = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    """Elimina el like de una canción.

    Requiere autenticación: Header `Authorization: Bearer <token>`.
    """
    repo = LikedSongsRepository(db)

    if not repo.remove(user_id, song_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Song not found in your likes"
        )

    db.commit()
    return None


@router.get(
    "/",
    response_model=List[LikedSongRead],
    responses={**AUTH_RESPONSES},
)
def list_liked_songs(
    user_id: int = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    """Lista tus canciones con like.

    Requiere autenticación: Header `Authorization: Bearer <token>`.
    """
    repo = LikedSongsRepository(db)
    entries = repo.list_by_user(user_id)
    return [LikedSongRead.model_validate(e) for e in entries]
