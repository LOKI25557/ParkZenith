from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from dotenv import load_dotenv
from typing import Optional, List, Union
import os

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "ParkZenith"
    ENVIRONMENT: str = "development"  # development, testing, production
    DEBUG: bool = True
    DATABASE_URL: str
    SECRET_KEY: str = "super-secret-key-change-me-in-production-environments-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Logging
    LOG_LEVEL: str = "INFO"

    # CORS Allowed Origins (comma-separated string, e.g. "http://localhost:3000,http://localhost:8000")
    ALLOWED_ORIGINS: str = "*"

    # AI Service Integration
    AI_SERVICE_URL: str = "http://localhost:8001"
    AI_SERVICE_TIMEOUT: float = 10.0
    AI_SERVICE_ENABLED: bool = True
    AI_SERVICE_RETRY_COUNT: int = 3

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY == "super-secret-key-change-me-in-production-environments-key":
                raise ValueError("SECRET_KEY must be changed in a production environment!")
            if len(self.SECRET_KEY) < 32:
                raise ValueError("SECRET_KEY must be at least 32 characters in a production environment!")
            # Force debug to False in production
            self.DEBUG = False
        return self


settings = Settings()
