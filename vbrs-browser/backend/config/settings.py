"""Central application configuration backed by pydantic-settings.

All environment-driven configuration must flow through :class:`Settings`.
Application code should call :func:`get_settings` (or the module-level
``settings`` instance) instead of reading environment variables directly.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Typed application settings loaded from environment variables / ``.env``.

    Field names map to environment variables case-insensitively
    (``es_url`` <-> ``ES_URL``, ``cors_origins`` <-> ``CORS_ORIGINS``).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    backend_host: str = "0.0.0.0"
    backend_port: int = Field(default=8000, ge=1, le=65535)

    # Allowed CORS origins; parsed as JSON when set via environment, e.g.
    #   CORS_ORIGINS=["http://localhost:5173"]
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]

    es_url: str = "http://localhost:9200"
    es_index: str = "dictionary"
    # Timeout (seconds) used for connectivity probes (e.g. the health ping).
    es_connect_timeout: float = Field(default=5.0, gt=0)
    # Default timeout (seconds) for Elasticsearch API operations.
    es_request_timeout: float = Field(default=30.0, gt=0)

    page_size: int = Field(default=20, ge=1)
    max_page_size: int = Field(default=100, ge=1)

    ingestion_batch_size: int = Field(default=1000, ge=1)

    log_level: LogLevel = LogLevel.INFO

    api_v1_prefix: str = "/api/v1"

    @field_validator("api_v1_prefix")
    @classmethod
    def _validate_api_prefix(cls, value: str) -> str:
        if not value.startswith("/") or value.endswith("/"):
            raise ValueError("api_v1_prefix must start with '/' and not end with '/'")
        return value

    @model_validator(mode="after")
    def _validate_pagination_limits(self) -> Settings:
        if self.page_size > self.max_page_size:
            raise ValueError("page_size must not exceed max_page_size")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


# Convenience instance for modules that want configuration at import time.
settings = get_settings()
