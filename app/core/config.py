# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    ENVIRONMENT: str = Field(default="dev")
    API_V1_PREFIX: str = Field(default="/api/v1")
    DATABASE_URL: str | None = None
    ASAAS_API_BASE: str = Field(default="https://api.asaas.com/v3")

    # JWT
    SECRET_KEY: str = Field(default="changeme")  # troque em prod
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=120)

settings = Settings()
