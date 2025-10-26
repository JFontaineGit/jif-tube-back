from fastapi import APIRouter, Depends, Path, HTTPException, status
from sqlmodel import Session
from typing import List
from uuid import UUID
from app.db.session import get_db
from app.repositories.library import LibraryRepository
from app.repositories.songs import SongsRepository
from app.schemas.library import LibraryItemCreate, LibraryItemRead
from app.api.dependencies import get_user_id

router = APIRouter(prefix="/library", tags=["Library"])

AUTH_RESPONSES = {
    status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid access token"}
}


@router.post(
    "/",
    response_model=LibraryItemRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        **AUTH_RESPONSES,
        status.HTTP_404_NOT_FOUND: {"description": "Song not found"},
        status.HTTP_409_CONFLICT: {"description": "Song already stored in library"},
    },
)
def add_to_library(
    item: LibraryItemCreate,
    user_id: UUID = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    """
    Agrega una canción a tu biblioteca personal.
    
    - **song_id**: YouTube video ID de la canción
    
    Requiere autenticación: Header `Authorization: Bearer <token>`.
    """
    repo = LibraryRepository(db)
    songs_repo = SongsRepository(db)
    
    # Verificar que la song exista
    song = songs_repo.get_by_id(item.song_id)
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Song {item.song_id} not found. Search it first."
        )
    
    try:
        entry = repo.add(user_id, item.song_id)
        db.commit()
        return LibraryItemRead.model_validate(entry)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.delete(
    "/{song_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **AUTH_RESPONSES,
        status.HTTP_404_NOT_FOUND: {"description": "Song not found in your library"},
    },
)
def remove_from_library(
    song_id: str = Path(..., min_length=10, max_length=15, description="YouTube video ID"),
    user_id: UUID = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    """
    Remueve una canción de tu biblioteca.
    
    Requiere autenticación: Header `Authorization: Bearer <token>`.
    """
    repo = LibraryRepository(db)
    
    if not repo.remove(user_id, song_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Song not found in your library"
        )
    
    db.commit()
    return None 


@router.get(
    "/",
    response_model=List[LibraryItemRead],
    responses={**AUTH_RESPONSES},
)
def list_library(
    user_id: UUID = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    """
    Lista todas las canciones en tu biblioteca.
    
    Requiere autenticación: Header `Authorization: Bearer <token>`.
    """
    repo = LibraryRepository(db)
    entries = repo.list_by_user(user_id)
    return [LibraryItemRead.model_validate(e) for e in entries]