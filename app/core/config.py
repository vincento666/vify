from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.database_url_policy import DEFAULT_MYSQL8_DATABASE_URL, assert_mysql8_database_url


class Settings(BaseSettings):
    app_name: str = "Hify"
    api_prefix: str = "/api/v1"
    database_url: str = DEFAULT_MYSQL8_DATABASE_URL
    redis_url: str | None = None
    log_level: str = "INFO"
    persistence_mode: str = "local"
    runtime_lab_sop_chatflow_ids: str | None = None
    runtime_lab_sop_runtime_invocation_mode: str = "sync"
    runtime_lab_intent_arbitrator_mode: str = "fake"
    runtime_lab_intent_arbitrator_base_url: str | None = None
    runtime_lab_intent_arbitrator_api_key: str | None = None
    runtime_lab_intent_arbitrator_model: str = "xiaomi/mimo-v2-flash"
    runtime_lab_intent_arbitrator_fallback_model: str | None = "deepseek/deepseek-v4-flash"
    runtime_lab_faq_knowledge_base_ids: str | None = None
    runtime_lab_rag_knowledge_base_ids: str | None = None
    customer_assistant_llm_shadow_mode: str = "off"
    customer_assistant_llm_shadow_model_config_id: int | None = None
    customer_assistant_llm_shadow_task_recognition: bool = True
    customer_assistant_llm_shadow_recommendation: bool = True
    customer_assistant_llm_runtime_mode: str = "llm_primary_with_fallback"
    customer_assistant_llm_primary_model_config_id: int | None = None
    customer_assistant_llm_primary_min_confidence: float = 0.70
    customer_assistant_worker_wait_deadline_seconds: float | None = None
    customer_assistant_worker_timeout_seconds: float = 5.0
    customer_assistant_stub_qa_delay_seconds: float = 0.0
    customer_assistant_worker_profiles_json: str | None = None
    ai_assistant_llm_mode: str = "deterministic"
    ai_assistant_openrouter_base_url: str = "https://openrouter.ai/api/v1"
    ai_assistant_openrouter_model: str = "qwen/qwen3.5-27b"
    ai_assistant_openrouter_api_key: str = ""
    ai_assistant_openrouter_api_key_env: str = "OPENROUTER_API_KEY"

    model_config = SettingsConfigDict(env_prefix="HIFY_", env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_database_url(self) -> "Settings":
        assert_mysql8_database_url(self.database_url)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
