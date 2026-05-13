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

    # --- Phase 3: Overreach LLM controls ---
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    overreach_enabled: bool = Field(default=True, alias="OVERREACH_ENABLED")
    overreach_model: str = Field(default="claude-sonnet-4-6", alias="OVERREACH_MODEL")
    overreach_daily_usd_cap: float = Field(default=50.0, alias="OVERREACH_DAILY_USD_CAP")
    overreach_rate_limit_per_hour: int = Field(default=3, alias="OVERREACH_RATE_LIMIT_PER_HOUR")


@lru_cache
def get_settings() -> Settings:
    return Settings()
