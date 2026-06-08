from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Hify"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./hify.db"
    redis_url: str | None = None
    log_level: str = "INFO"
    runtime_lab_sop_chatflow_ids: str | None = None
    runtime_lab_intent_arbitrator_mode: str = "fake"
    runtime_lab_intent_arbitrator_base_url: str | None = None
    runtime_lab_intent_arbitrator_api_key: str | None = None
    runtime_lab_intent_arbitrator_model: str = "xiaomi/mimo-v2-flash"
    runtime_lab_intent_arbitrator_fallback_model: str | None = "deepseek/deepseek-v4-flash"
    runtime_lab_faq_knowledge_base_ids: str | None = None
    runtime_lab_rag_knowledge_base_ids: str | None = None

    model_config = SettingsConfigDict(env_prefix="HIFY_", env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
