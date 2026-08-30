"""Application configuration.

Reads settings from environment variables / a local `.env` file via
`pydantic-settings`. This module is infrastructure (not domain), so it is
allowed to depend on third-party config machinery -- but it must stay free
of framework code (no FastAPI, SQLAlchemy, redis-py, etc. imports here),
since it is imported very early by everything else.
"""

from datetime import date
from decimal import Decimal
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized application settings, loaded from `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Postgres -----------------------------------------------------
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "jobact"
    postgres_password: str = "jobact"
    postgres_db: str = "jobact"
    # The local Compose Postgres has no SSL configured at all. asyncpg's
    # default 'prefer' negotiation (try SSL, fall back to plaintext) hangs
    # into a connection-reset instead of falling back on Windows'
    # ProactorEventLoop, so it must be disabled outright for local/dev use.
    # Flip to true once a target Postgres (e.g. managed production) actually
    # terminates TLS.
    postgres_ssl: bool = False

    @property
    def database_url(self) -> str:
        """Async SQLAlchemy connection URL assembled from the pieces above."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # --- Redis ----------------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"

    # --- MinIO / S3 -------------------------------------------------------
    minio_endpoint_url: str = "http://localhost:9000"
    # Browser-facing origin used when signing upload/download URLs. In Docker,
    # `minio` is resolvable only by containers, while the browser uses localhost.
    minio_public_endpoint_url: str = "http://localhost:9000"
    minio_access_key: str = "jobact"
    minio_secret_key: str = "jobact-secret"
    minio_bucket_name: str = "jobact-reports"

    # --- LiteLLM proxy ------------------------------------------------
    litellm_base_url: str = "http://localhost:4000"
    litellm_master_key: str = "sk-jobact-litellm"
    openrouter_api_key: str = ""
    anthropic_api_key: str = ""
    dashscope_api_key: str = ""
    qwen_base_url: str = (
        "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    )

    # --- External call timeouts ---------------------------------------
    # Every outbound AI/storage call is bounded so a hung provider parks
    # the workflow in MANUAL_INPUT_REQUIRED instead of stalling forever.
    ai_request_timeout_seconds: float = 600.0
    ai_connect_timeout_seconds: float = 5.0
    object_storage_connect_timeout_seconds: float = 5.0
    object_storage_read_timeout_seconds: float = 20.0
    pdf_render_timeout_seconds: float = 15.0

    # --- Local, deliberately dated FX snapshot -----------------------
    usd_rub_rate: Decimal = Decimal("84.4635")
    usd_rub_rate_date: date = date(2026, 8, 26)
    usd_rub_rate_source: str = "CBR"

    # --- Google OAuth (not wired up until the auth task) -----------------
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_url: str = "http://localhost:8000/auth/google/callback"

    # --- Session cookie -------------------------------------------------
    session_cookie_name: str = "jobact_session"
    session_secret: str = "change-me"

    # --- CORS / allowed origins ------------------------------------------
    app_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def app_origins_list(self) -> list[str]:
        """`app_origins` split into a list, for use as a CORS allowlist."""
        return [origin.strip() for origin in self.app_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide cached `Settings` instance."""
    return Settings()
