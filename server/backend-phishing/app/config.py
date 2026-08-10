"""Typed runtime configuration for a campaign backend."""

from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Load and validate the environment contract for one campaign."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    # Campaign identity and runtime mode
    ENVIRONMENT: Literal["development", "production"] = "production"
    CAMPAIGN_ID: str = Field(min_length=1)
    CAMPAIGN_PROTOCOL: Literal["vnc", "selkies"] = "vnc"

    # Internal authentication
    INTERNAL_API_KEY: str = Field(min_length=1)
    GATEWAY_AUTH_KEY: str = Field(min_length=1)
    SESSION_TOKEN_SECRET: str = Field(min_length=1)

    # Persistence and internal services
    DB_PATH: str = "/storage/p-bitm.db"
    STORAGE_PATH: str = "/storage"
    ADMIN_API_URL: str = Field(
        default="http://bitm-backend:8443",
        validation_alias=AliasChoices(
            "ADMIN_API_URL",
            "ADMIN_BACKEND_URL",
        ),
    )

    # Worker and admission limits
    SESSION_TOKEN_TTL_SECONDS: int = Field(default=300, gt=0)
    WS_HANDSHAKE_TIMEOUT_SECONDS: float = Field(default=10, gt=0)
    WS_SESSION_STARTUP_TIMEOUT_SECONDS: float = Field(default=45, gt=0)
    MAX_ACTIVE_SESSIONS: int = Field(default=20, gt=0)
    WS_RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60, gt=0)
    WS_RATE_LIMIT_MAX_ATTEMPTS: int = Field(default=10, gt=0)
    WS_GLOBAL_RATE_LIMIT_MAX_ATTEMPTS: int = Field(default=200, gt=0)
    WS_MAX_MESSAGE_BYTES: int = Field(
        default=256 * 1024,
        ge=4 * 1024,
        le=2 * 1024 * 1024,
    )
    WS_MESSAGE_RATE_WINDOW_SECONDS: int = Field(default=10, gt=0)
    WS_MESSAGE_RATE_MAX_MESSAGES: int = Field(default=100, gt=0)
    WS_MAX_QUEUE: int = Field(default=32, gt=0, le=256)
    WS_MAX_WEBRTC_CANDIDATES: int = Field(default=64, gt=0, le=256)
    STREAM_ACCESS_TTL_SECONDS: int = Field(default=86400, gt=0)
    TRACKING_QUEUE_SIZE: int = Field(default=256, gt=0, le=10_000)
    TRACKING_WORKERS: int = Field(default=4, gt=0, le=16)
    TRACKING_RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60, gt=0)
    TRACKING_RATE_LIMIT_PER_CLIENT: int = Field(default=120, gt=0)
    TRACKING_RATE_LIMIT_GLOBAL: int = Field(default=1000, gt=0)

    # Public routes and cookies
    ENTRY_PATH: str = "continue"
    TRACKING_PARAMETER: str = ""
    STREAM_PATH: str = "assets"
    LANDING_COOKIE_NAME: str = "browser_session"
    STREAM_COOKIE_NAME: str = "media_session"

    # Target site
    IP: str = "localhost"
    URL: str = "https://duckduckgo.com/"
    CAMPAIGN_HOST: str = "bitm.local"


settings = Settings()
