from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+asyncpg://postgres:development-only-change-me@localhost:5432/acoustic_livestock"
    )
    device_hmac_secret: str = "development-only-device-hmac-secret-change-before-deployment"

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")


settings = Settings()
