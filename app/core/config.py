from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="cache-distribuido-lab", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")

    database_url: str = Field(
        default="postgresql+asyncpg://cache_lab:cache_lab@localhost:5432/cache_lab",
        alias="DATABASE_URL",
    )

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_ttl_seconds: int = Field(default=60, alias="REDIS_TTL_SECONDS")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
