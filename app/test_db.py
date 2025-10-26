from app.db.session import SessionLocal, create_db_and_tables
from app.repositories import *
from app.models import User
from app.schemas.songs import SongCreate
from datetime import datetime, timezone

# Crear tablas (solo para test)
create_db_and_tables()

# Test básico
with SessionLocal() as session:
    users_repo = UsersRepository(session)
    songs_repo = SongsRepository(session)
    library_repo = LibraryRepository(session)
    liked_repo = LikedSongsRepository(session)
    cache_repo = CacheRepository(session)
    search_repo = SearchRepository(session)
    
    try:
        # 1. Crear user
        user = User(
            username="testpibe",
            email="test@ejemplo.com",
            password_hash="hashedpass",
            role="user",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        created_user = users_repo.create(user)
        session.commit()
        assert created_user.id is not None
        print(f"User creado: {created_user.username}")
        
        # 2. Crear song
        song_data = SongCreate(
            id="dQw4w9WgXcQ",
            title="Never Gonna Give You Up",
            channel_title="Rick Astley"
        )
        song = songs_repo.get_or_create_from_youtube_meta(song_data)
        session.commit()
        assert song.id == "dQw4w9WgXcQ"
        print(f"Song creado: {song.title}")
        
        # 3. Add to library
        entry = library_repo.add(created_user.id, song.id)
        session.commit()
        assert entry.user_id == created_user.id
        print(f"Song agregado a library")

        # 4. List library
        library = library_repo.list_by_user(created_user.id)
        assert len(library) == 1
        print(f"Library tiene {len(library)} song(s)")

        # 5. Like song
        like = liked_repo.add(created_user.id, song.id)
        session.commit()
        assert like.user_id == created_user.id
        print("Song marcado como like")

        liked = liked_repo.list_by_user(created_user.id)
        assert len(liked) == 1
        print(f"Likes tiene {len(liked)} song(s)")

        # 6. Test cache
        cache_repo.set("test_key", {"foo": "bar"}, ttl_minutes=1)
        session.commit()
        cached = cache_repo.get("test_key")
        assert cached == {"foo": "bar"}
        print(f"✅ Cache funcionando")

        # 7. Log search
        search = search_repo.log_search(created_user.id, "test query")
        session.commit()
        assert search.count == 1
        print(f"✅ Search logged")
        
        print("\nTodos los tests pasaron")
        
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        raise
