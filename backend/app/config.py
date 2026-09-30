from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "SIH 2026 Acoustic Livestock Health System"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Database Settings
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres_password_sih2026"
    POSTGRES_DB: str = "acoustic_livestock_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: Optional[str] = None

    # Service Integration URLs
    ML_SERVICE_URL: str = "http://localhost:8001"

    # Security & Secret Key
    SECRET_KEY: str = "sih_2026_acoustic_livestock_health_secret_key_change_in_production"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()
