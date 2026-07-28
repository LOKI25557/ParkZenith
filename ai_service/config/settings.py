"""
Configuration settings for ParkZenith AI Service using Pydantic Settings.
Reads configuration from environment variables or .env file.
"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings for AI Service.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    APP_NAME: str = "ParkZenith AI Service"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Database Configuration
    # Supports PostgreSQL (asyncpg) or SQLite (aiosqlite)
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./ai_service.db",
        description="Async database connection URL",
    )
    DB_ECHO: bool = False

    # Backend API Client Configuration
    BACKEND_API_URL: str = Field(
        default="http://localhost:8000/api/v1",
        description="Base URL of the main ParkZenith backend API",
    )
    BACKEND_API_KEY: Optional[str] = Field(
        default=None,
        description="Optional API key for authenticating with main backend",
    )
    HTTP_TIMEOUT_SECONDS: float = Field(
        default=10.0, description="HTTP request timeout in seconds"
    )
    HTTP_MAX_RETRIES: int = Field(
        default=3, description="Maximum retries for failed HTTP requests"
    )
    HTTP_RETRY_BACKOFF_FACTOR: float = Field(
        default=0.5, description="Backoff factor for HTTP retries"
    )

    # Collector Job Intervals (in seconds)
    OCCUPANCY_COLLECTION_INTERVAL_SECONDS: int = Field(
        default=60, description="Interval for collecting occupancy data (1 minute)"
    )
    RESERVATION_COLLECTION_INTERVAL_SECONDS: int = Field(
        default=300, description="Interval for collecting reservation data (5 minutes)"
    )
    SESSION_COLLECTION_INTERVAL_SECONDS: int = Field(
        default=300, description="Interval for collecting parking session data (5 minutes)"
    )

    # Dataset Export Settings
    EXPORT_PATH: str = Field(
        default="./datasets",
        description="Directory path for exporting dataset CSV files",
    )


settings = Settings()
