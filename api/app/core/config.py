from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(
        default="postgresql+asyncpg://inkling:inkling@localhost:5432/inkling",
        alias="DATABASE_URL",
    )
    api_secret_key: str = Field(default="dev-secret-change-me", alias="API_SECRET_KEY")
    session_ttl_days: int = Field(default=7, alias="SESSION_TTL_DAYS")
    age_gate_min: int = Field(default=18, alias="AGE_GATE_MIN")
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])


@lru_cache
def get_settings() -> Settings:
    return Settings()
