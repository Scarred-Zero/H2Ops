import os
import sys
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT_FOR_IMPORTS = Path(__file__).resolve().parents[1]
PACKAGE_ROOT_FOR_IMPORTS = Path(__file__).resolve().parent
for candidate in (PROJECT_ROOT_FOR_IMPORTS, PACKAGE_ROOT_FOR_IMPORTS):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from src.utils.path_utils import find_project_root


# UTILITY FUNCTION TO FIND .ENV FILE FROM PROJECT ROOT
def _find_env_file(start_path: Path) -> Path | None:
    for candidate in (start_path, *start_path.parents):
        env_file = candidate / ".env.development.local"
        if env_file.exists():
            return env_file
    return None


# BOOTSTRAP PROJECT ROOT AND FIND .ENV FILE
PROJECT_ROOT = find_project_root(Path(__file__).resolve().parent)
ENV_FILE = _find_env_file(Path(__file__).resolve().parent)


# UTILITY FUNCTION TO RESOLVE HOSTS BASED ON ENVIRONMENT
def _normalize_runtime_host(host: str) -> str:
    if host in {"host.docker.internal", "host-gateway", "gateway.docker.internal"}:
        return "localhost"
    return host


def _resolve_host(default_host: str, env_name: str) -> str:
    configured_host = os.getenv(env_name, default_host)
    if os.getenv("DOCKER_CONTAINER") == "true":
        return configured_host
    return _normalize_runtime_host(configured_host)


# SETTINGS CLASS USING Pydantic
class Settings(BaseSettings):
    # GENERAL SETTINGS
    ENVIRONMENT: str = "development"
    APP_NAME: str = "H2Ops"
    APP_VERSION: str = "0.1.0"
    APP_SECRET_KEY: str = os.getenv("APP_SECRET_KEY", "dev-secret-key-change-me")
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # ERROR TRACKING WITH SENTRY
    SENTRY_DSN: str | None = os.getenv("SENTRY_DSN", None)

    # DATABASE SETTINGS
    POSTGRES_HOST: str = _resolve_host("localhost", "POSTGRES_HOST")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", 5433))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "h2ops_dev_db")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "h2ops_dev_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "dev_password")
    DATABASE_URL: str = ""

    # REDIS SETTINGS
    REDIS_HOST: str = _resolve_host("localhost", "REDIS_HOST")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB: int = int(os.getenv("REDIS_DB", 0))
    REDIS_URL: str = ""

    # CELERY SETTINGS
    DEFAULT_BROKER: str = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", DEFAULT_BROKER)
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", DEFAULT_BROKER)

    # MINIO SETTINGS
    MINIO_HOST: str = _resolve_host("localhost", "MINIO_HOST")
    MINIO_PORT: int = int(os.getenv("MINIO_PORT", 9000))
    MINIO_ENDPOINT: str = ""
    MINIO_PUBLIC_URL: str = os.getenv("MINIO_PUBLIC_URL", "")
    MINIO_ROOT_USER: str = os.getenv("MINIO_ROOT_USER", "minioadmin")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_ROOT_PASSWORD: str = os.getenv("MINIO_ROOT_PASSWORD", "minioadminpassword")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadminpassword")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "reports")
    MINIO_USE_SSL: bool = False

    # JWT SETTINGS
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-key-change-me")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_MINUTES: int = os.getenv("JWT_ACCESS_TOKEN_MINUTES", 20)
    REFRESH_TOKEN_EXPIRE_DAYS: int = os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7)
    COOKIE_DOMAIN: str = os.getenv("COOKIE_DOMAIN", "localhost")
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", False)

    # EMAIL SETTINGS
    SMTP_HOST: str | None = os.getenv("SMTP_HOST", None)
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER: str | None = os.getenv("SMTP_USER", None)
    SMTP_PASSWORD: str | None = os.getenv("SMTP_PASSWORD", None)
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", True)
    EMAILS_FROM_EMAIL: str | None = os.getenv("EMAILS_FROM_EMAIL", None)

    # VERIFICATION SETTINGS
    FRONTEND_VERIFY_URL: str = os.getenv(
        "FRONTEND_VERIFY_URL", "http://localhost:3000/verify-email"
    )
    FRONTEND_RESET_PASSWORD: str = os.getenv(
        "FRONTEND_RESET_PASSWORD", "http://localhost:3000/reset-password"
    )

    # CORS SETTINGS
    BACKEND_CORS_ORIGINS: list[str] | str = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            # If empty string, return empty list
            if not v.strip():
                return []
            # Handles plain strings or comma-separated lists
            return [
                origin.strip().strip('"').strip("'")
                for origin in v.split(",")
                if origin.strip()
            ]
        return v

    # MODEL CONFIGURATION
    model_config = SettingsConfigDict(
        env_file=ENV_FILE or (PROJECT_ROOT / ".env.dev.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # URL INITIALIZATION BASED ON ENVIRONMENT
    def model_post_init(self, __context) -> None:  # noqa: ARG002
        db_host = os.getenv("POSTGRES_HOST", self.POSTGRES_HOST)
        redis_host = os.getenv("REDIS_HOST", self.REDIS_HOST)
        minio_host = os.getenv("MINIO_HOST", self.MINIO_HOST)

        # RESOLVE HOSTS IF RUNNING INSIDE A DOCKER CONTAINER
        if os.getenv("DOCKER_CONTAINER") == "true":
            db_host = os.getenv("POSTGRES_HOST", "db")
            redis_host = os.getenv("REDIS_HOST", "redis")
            minio_host = os.getenv("MINIO_HOST", "minio")
        else:
            db_host = _normalize_runtime_host(db_host)
            redis_host = _normalize_runtime_host(redis_host)
            minio_host = _normalize_runtime_host(minio_host)

        # INITIALIZE URLS IF NOT PROVIDED
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
                f"{db_host}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        if not self.REDIS_URL:
            self.REDIS_URL = f"redis://{redis_host}:{self.REDIS_PORT}/{self.REDIS_DB}"
        if not self.MINIO_ENDPOINT:
            self.MINIO_ENDPOINT = f"{minio_host}:{self.MINIO_PORT}"
        if not self.MINIO_PUBLIC_URL:
            self.MINIO_PUBLIC_URL = f"http://localhost:{self.MINIO_PORT}"


settings = Settings()
