from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel
from app.core.config import settings

# Engine sync (para start; async en futuro)
engine = create_engine(
    str(settings.DATABASE_URL),
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

# Sessionmaker para transacciones
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine, 
    class_=Session
)

# Dependency para FastAPI
def get_db():
    """Dependency que provee DB session con context manager."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# Helper para crear tablas (solo dev/tests)
def create_db_and_tables():
    """Crea todas las tablas. Usar Alembic en prod."""
    SQLModel.metadata.create_all(engine)