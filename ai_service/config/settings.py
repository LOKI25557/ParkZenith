"""
Configuration settings for ParkZenith AI Service using Pydantic Settings.
Reads configuration from environment variables or .env file.
"""

from typing import Optional
from pydantic import Field, model_validator
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

    # Production AI/ML Orchestration Configurations
    FORECAST_HORIZONS: str = Field(
        default="15,30,60",
        description="Supported prediction horizons in minutes separated by commas"
    )

    # Availability Risk Thresholds
    AVAILABILITY_HIGH_RISK_THRESHOLD: float = Field(
        default=90.0,
        description="Occupancy percentage above which risk is HIGH"
    )
    AVAILABILITY_MEDIUM_RISK_THRESHOLD: float = Field(
        default=70.0,
        description="Occupancy percentage above which risk is MEDIUM"
    )
    AVAILABILITY_HIGH_PROB_FULL_THRESHOLD: float = Field(
        default=70.0,
        description="Full probability percentage above which risk is HIGH"
    )
    AVAILABILITY_MEDIUM_PROB_FULL_THRESHOLD: float = Field(
        default=20.0,
        description="Full probability percentage above which risk is MEDIUM"
    )

    # Recommendation Weights (Must sum to 1.0)
    RECOMMENDATION_WEIGHT_AVAILABILITY: float = Field(default=0.30)
    RECOMMENDATION_WEIGHT_DISTANCE: float = Field(default=0.20)
    RECOMMENDATION_WEIGHT_FORECAST: float = Field(default=0.15)
    RECOMMENDATION_WEIGHT_CURRENT_OCCUPANCY: float = Field(default=0.10)
    RECOMMENDATION_WEIGHT_WALKING_DISTANCE: float = Field(default=0.10)
    RECOMMENDATION_WEIGHT_HISTORICAL_UTILIZATION: float = Field(default=0.05)
    RECOMMENDATION_WEIGHT_PARKING_COST: float = Field(default=0.05)
    RECOMMENDATION_WEIGHT_QUEUE_CONGESTION: float = Field(default=0.05)

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            if self.BACKEND_API_KEY and self.BACKEND_API_KEY in ("default_key", "backend-api-key", ""):
                raise ValueError("BACKEND_API_KEY must be configured with a secure value in production!")
            # Force DB echo off in production
            self.DB_ECHO = False
        return self


settings = Settings()
