"""
Application configuration.

All settings are loaded from environment variables (or .env file).
Access the singleton via: from app.config import settings
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    api_host: str = "localhost"
    api_port: int = 8000

    database_url: str = (
        "postgresql+asyncpg://warehouse:warehouse@localhost:5433/warehouse"
    )

    ocr_languages: list[str] = ["en"]
    ocr_use_gpu: bool = False

    min_confidence: float = 0.0


settings = Settings()
