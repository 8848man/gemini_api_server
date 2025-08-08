from functools import lru_cache
from typing import List

from decouple import config
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Configuration
    API_HOST: str = config("API_HOST", default="0.0.0.0")
    API_PORT: int = config("API_PORT", default=8000, cast=int)
    API_WORKERS: int = config("API_WORKERS", default=1, cast=int)
    DEBUG: bool = config("DEBUG", default=False, cast=bool)

    # Security
    SECRET_KEY: str = config("SECRET_KEY", default="dev-secret-key")
    API_KEY: str = config("API_KEY", default="dev-api-key")
    JWT_SECRET_KEY: str = config("JWT_SECRET_KEY", default="dev-jwt-secret")
    JWT_ALGORITHM: str = config("JWT_ALGORITHM", default="HS256")
    JWT_EXPIRATION_HOURS: int = config("JWT_EXPIRATION_HOURS", default=24, cast=int)

    # Google Gemini API
    GEMINI_API_KEY: str = config("GEMINI_API_KEY", default="")
    GEMINI_MODEL: str = config("GEMINI_MODEL", default="gemini-2.0-flash")

    # Redis Configuration
    REDIS_URL: str = config("REDIS_URL", default="redis://localhost:6379/0")
    REDIS_PASSWORD: str = config("REDIS_PASSWORD", default="")

    # Rate Limiting
    REQUESTS_PER_MINUTE: int = config("REQUESTS_PER_MINUTE", default=60, cast=int)
    MAX_CONCURRENT_REQUESTS: int = config("MAX_CONCURRENT_REQUESTS", default=3, cast=int)
    DUPLICATE_REQUEST_WINDOW_MINUTES: int = config(
        "DUPLICATE_REQUEST_WINDOW_MINUTES", default=10, cast=int
    )

    # CORS
    ALLOWED_ORIGINS: List[str] = config(
        "ALLOWED_ORIGINS",
        default="http://localhost:3000,http://127.0.0.1:3000",
        cast=lambda v: [s.strip() for s in v.split(",")],
    )
    ALLOWED_METHODS: List[str] = config(
        "ALLOWED_METHODS",
        default="GET,POST,PUT,DELETE,OPTIONS",
        cast=lambda v: [s.strip() for s in v.split(",")],
    )
    ALLOWED_HEADERS: List[str] = config(
        "ALLOWED_HEADERS",
        default="*",
        cast=lambda v: [s.strip() for s in v.split(",")],
    )

    # Logging
    LOG_LEVEL: str = config("LOG_LEVEL", default="INFO")
    LOG_FILE: str = config("LOG_FILE", default="logs/app.log")

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()