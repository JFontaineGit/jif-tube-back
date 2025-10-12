from typing import Optional, List, Dict
from sqlmodel import SQLModel, Field, Relationship, JSON
from passlib.context import CryptContext
from datetime import datetime, timezone

# Configuración de hashing (global, usado en services)
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

class PasswordError(Exception):
    """Exception raised for errors in password validation."""
    def __init__(self, message: str = "Invalid password"):
        super().__init__(message)
        self.message = message

class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=100, unique=True, index=True)
    email: str = Field(max_length=255, unique=True, index=True)
    password_hash: str = Field(max_length=255)
    role: str = Field(default="user", max_length=30)
    is_active: bool = Field(default=True)
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default=None)
    
    # Relaciones
    search_history: List["SearchHistory"] = Relationship(back_populates="user")
    library: List["UserLibrary"] = Relationship(back_populates="user")

class SearchHistory(SQLModel, table=True):
    __tablename__ = "search_history"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    query: str = Field(max_length=500)
    timestamp: int  # UNIX epoch ms
    count: int = Field(default=1)
    user_id: Optional[int] = Field(foreign_key="users.id")
    
    user: Optional[User] = Relationship(back_populates="search_history")

class CacheEntry(SQLModel, table=True):
    __tablename__ = "cache_entries"
    
    cache_key: str = Field(primary_key=True, max_length=255)
    data: Dict = Field(sa_type=JSON)  # jsonb
    timestamp: int  # UNIX epoch ms
    ttl_minutes: int = Field(default=60)

class Song(SQLModel, table=True):
    __tablename__ = "songs"
    
    id: str = Field(primary_key=True, max_length=255)  # YouTube video_id
    title: str = Field(max_length=255)
    channel_title: Optional[str] = Field(default=None, max_length=255)
    duration: Optional[str] = Field(default=None, max_length=50)
    thumbnails: Optional[Dict] = Field(default=None, sa_type=JSON)  # jsonb
    published_at: Optional[datetime] = Field(default=None)
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    library_entries: List["UserLibrary"] = Relationship(back_populates="song")

class UserLibrary(SQLModel, table=True):
    __tablename__ = "user_library"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    song_id: str = Field(foreign_key="songs.id", max_length=255)
    added_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    user: Optional[User] = Relationship(back_populates="library")
    song: Optional[Song] = Relationship(back_populates="library_entries")