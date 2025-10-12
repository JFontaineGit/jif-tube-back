from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path
from app.core.config import settings, validate_settings
from app.db.session import create_db_and_tables, SessionLocal
from app.api import auth, users, search, songs, library 
from app.services.cache_service import CacheService
from app.repositories.users import UsersRepository
from app.models import User
from app.core.security import hash_password
from datetime import datetime, timezone
import logging

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager para startup/shutdown.
    """
    # =========================================================================
    # STARTUP
    # =========================================================================
    logger.info("=" * 60)
    logger.info("🚀 Starting JIF-TUBE Backend")
    logger.info("=" * 60)
    
    # Validar settings
    try:
        validate_settings()
        logger.info("✅ Settings validated")
    except ValueError as e:
        logger.error(f"❌ Settings validation failed: {e}")
        raise
    
    logger.info(f"📍 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🔧 Debug mode: {settings.DEBUG}")
    logger.info(f"🌐 CORS origins: {settings.cors_origins_list}")
    
    # Crear tablas (solo en development)
    if settings.is_development:
        try:
            create_db_and_tables()
            logger.info("✅ Database tables created/verified")
        except Exception as e:
            logger.error(f"❌ Error creating tables: {e}")
            raise
    
    # Crear usuario admin (solo en development)
    if settings.is_development:
        with SessionLocal() as session:
            users_repo = UsersRepository(session)
            admin = users_repo.get_by_username("admin")
            
            if not admin:
                try:
                    admin_user = User(
                        username="admin",
                        email="admin@jiftube.local",
                        password_hash=hash_password("adminpass"),
                        role="admin",
                        is_active=True,
                        created_at=datetime.now(timezone.utc)
                    )
                    users_repo.create(admin_user)
                    session.commit()
                    logger.info("✅ Admin user created (admin/adminpass)")
                except Exception as e:
                    logger.error(f"❌ Error creating admin: {e}")
                    session.rollback()
            else:
                logger.info("ℹ️  Admin user already exists")
    
    # Cleanup cache expirado
    with SessionLocal() as session:
        try:
            cache_service = CacheService(session)
            deleted = cache_service.cleanup_expired()
            logger.info(f"🧹 Cleaned {deleted} expired cache entries")
        except Exception as e:
            logger.warning(f"⚠️  Cache cleanup failed: {e}")
    
    logger.info("=" * 60)
    logger.info("✅ Server ready!")
    logger.info(f"📚 API Docs: http://localhost:8000/docs")
    logger.info("=" * 60)
    
    yield
    
    logger.info("Shutting down JIF-TUBE Backend...")
    
    # Final cache cleanup
    with SessionLocal() as session:
        try:
            cache_service = CacheService(session)
            deleted = cache_service.cleanup_expired()
            logger.info(f"🧹 Final cleanup: {deleted} expired entries")
        except Exception as e:
            logger.warning(f"⚠️  Final cleanup failed: {e}")
    
    logger.info("👋 Goodbye!")


app = FastAPI(
    title="JIF-TUBE API",
    description="""
    Backend API para reproductor de música usando YouTube.
    
    ## Features
    
    * **Autenticación JWT**: Register, login, refresh tokens
    * **Búsqueda**: Busca canciones en YouTube con cache inteligente
    * **Biblioteca personal**: Guarda tus canciones favoritas
    * **Historial**: Tracking de búsquedas
    
    ## Auth
    
    Usa el endpoint `/api/auth/login` para obtener tokens.
    Luego incluye el access token en el header: `Authorization: Bearer <token>`
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# MIDDLEWARE
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# SPA

class SPAStatic(StaticFiles):
    def __init__(self, directory: Path, html: bool = True, check_dir: bool = True, index_html: Path = Path("index.html")):
        super().__init__(directory=directory, html=html, check_dir=check_dir)
        self.index_html = index_html
        self.app = super().__call__

    async def __call__(self, scope, receive, send):
        assert scope["type"] == "http"

        request = Request(scope, receive)
        path = request.url.path.lstrip("/")

        # Excluir /api routes (maneja backend)
        if request.url.path.startswith("/api"):
            await self.app(scope, receive, send)
            return

        # Si path existe, sirve static
        full_path = (Path(self.directory) / path).resolve()
        if full_path.exists():
            await self.app(scope, receive, send)
            return

        # Fallback a index.html para SPA routing
        index_path = Path(self.directory) / self.index_html
        response = FileResponse(index_path)
        return response(scope, receive, send)

# Monta SPA (asume frontend en ./frontend/dist o ./static; ajusta path)
FRONTEND_DIR = Path("frontend/dist")  # O "static" si lo buildés ahí
if FRONTEND_DIR.exists():
    app.mount("/", SPAStatic(directory=FRONTEND_DIR, html=True), name="spa")
    logger.info(f"✅ SPA mounted from {FRONTEND_DIR}")
else:
    logger.warning("⚠️  Frontend dir not found; API-only mode")

# ROUTERS

app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(songs.router, prefix="/api")
app.include_router(library.router, prefix="/api")

# GLOBAL ENDPOINTS

@app.get("/")
def root():
    """Root endpoint (SPA fallback si mounted)."""
    return {
        "message": "Welcome to JIF-TUBE API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG
    }


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler para errores de validación de Pydantic."""
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handler global para errores no manejados."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc) if settings.DEBUG else "An unexpected error occurred"
        }
    )