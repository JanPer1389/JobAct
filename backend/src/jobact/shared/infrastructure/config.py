"""Application configuration.

Reads settings from environment variables / a local `.env` file via
`pydantic-settings`. This module is infrastructure (not domain), so it is
allowed to depend on third-party config machinery -- but it must stay free
of framework code (no FastAPI, etc. imports here), since it is imported
very early by everything else.

Trimmed for the local-demo downgrade: the app no longer talks to
Postgres, Redis, MinIO, or an OAuth/session store, so their settings are
gone. What remains is exactly what the two stateless AI/STT endpoints and
the PDF renderer need.
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

    # --- Qwen / DashScope (the only AI connector) ----------------------
    dashscope_api_key: str = ""
    qwen_base_url: str = (
        "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    )

    # --- External call timeouts ---------------------------------------
    # Every outbound AI call is bounded so a hung provider fails the
    # request instead of stalling indefinitely.
    ai_request_timeout_seconds: float = 600.0
    ai_connect_timeout_seconds: float = 5.0
    pdf_render_timeout_seconds: float = 15.0

    # --- Local, deliberately dated FX snapshot -----------------------
    usd_rub_rate: Decimal = Decimal("84.4635")
    usd_rub_rate_date: date = date(2026, 8, 26)
    usd_rub_rate_source: str = "CBR"

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
