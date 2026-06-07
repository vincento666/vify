from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Hify"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./hify.db"
    redis_url: str | None = None
    log_level: str = "INFO"
    runtime_lab_sop_chatflow_ids: str | None = None

    model_config = SettingsConfigDict(env_prefix="HIFY_", env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
