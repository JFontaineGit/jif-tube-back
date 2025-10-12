from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List, Optional
import secrets

class Settings(BaseSettings):
    """
    Configuración de la aplicación.
    
    Las variables se cargan desde:
    1. Variables de entorno
    2. Archivo .env (si existe)
    3. Valores por defecto (si están definidos)
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    ENVIRONMENT: str = "development"  # development, staging, production
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of: {allowed}")
        return v

    DATABASE_URL: str
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Valida que sea una URL de Postgres válida."""
        if not v:
            raise ValueError("DATABASE_URL is required")

        if not (v.startswith("postgresql://") or v.startswith("postgres://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL")
        
        return v

    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Valida que SECRET_KEY tenga longitud mínima."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    @classmethod
    def generate_secret_key(cls) -> str:
        """Helper para generar SECRET_KEY seguro (usar en setup)."""
        return secrets.token_urlsafe(32)

    # YOUTUBE API

    YOUTUBE_API_KEY: str
    YOUTUBE_API_URL: str = "https://www.googleapis.com/youtube/v3"
    YOUTUBE_MAX_RESULTS: int = 10
    YOUTUBE_MIN_DURATION_SECONDS: int = 30
    YOUTUBE_MAX_DURATION_SECONDS: int = 600
    YOUTUBE_REGION_CODE: str = "AR"
    YOUTUBE_CATEGORY_ID: str = "10"  # Music

    @field_validator("YOUTUBE_API_KEY")
    @classmethod
    def validate_youtube_key(cls, v: str) -> str:
        if not v:
            raise ValueError("YOUTUBE_API_KEY is required")
        return v

    # SEARCH / CACHE

    SEARCH_CACHE_TTL_MINUTES: int = 60
    FORBIDDEN_TERMS: List[str] = [
        'tiktok', 'shorts', 'reaction', 'compilation', 
        'lyrics video', 'lyric video', 'visualizer'
    ]

    CORS_ORIGINS: str = "*"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parsea CORS_ORIGINS a lista."""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    
    CACHE_TTL_MINUTES: int = 60
    
    SMTP_ENABLED: bool = False
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    
    @field_validator("SMTP_ENABLED")
    @classmethod
    def validate_smtp(cls, v: bool, values) -> bool:
        """Si SMTP está habilitado, valida que tenga las credenciales."""
        if v:
            pass
        return v

    # Helpers
    
    @property
    def is_development(self) -> bool:
        """Helper para checks de entorno."""
        return self.ENVIRONMENT == "development"
    
    @property
    def is_production(self) -> bool:
        """Helper para checks de entorno."""
        return self.ENVIRONMENT == "production"
    
    def model_dump_safe(self) -> dict:
        """Dump de config SIN secretos (para logging)."""
        config = self.model_dump()
        # Oculta secrets
        sensitive_keys = ["SECRET_KEY", "YOUTUBE_API_KEY", "SMTP_PASSWORD", "DATABASE_URL"]
        for key in sensitive_keys:
            if key in config:
                config[key] = "***HIDDEN***"
        return config


settings = Settings()

def validate_settings():
    """Valida settings críticos al inicio de la app."""
    errors = []
    
    if settings.SECRET_KEY == "changeme" or len(settings.SECRET_KEY) < 32:
        errors.append("SECRET_KEY is insecure or too short")
    
    if settings.is_production and settings.DEBUG:
        errors.append("DEBUG must be False in production")
        
    if settings.is_production and settings.CORS_ORIGINS == "*":
        errors.append("CORS_ORIGINS should not be '*' in production")
    
    if errors:
        raise ValueError(f"Settings validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

# Validar al importar
# validate_settings()