from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from typing import Optional
import os

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "ParkZenith"
    DEBUG: bool = True
    DATABASE_URL: str
    SECRET_KEY: str = "super-secret-key-change-me-in-production-environments-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # AI Service Integration
    AI_SERVICE_URL: str = "http://localhost:8001"
    AI_SERVICE_TIMEOUT: float = 10.0
    AI_SERVICE_ENABLED: bool = True



settings = Settings()
