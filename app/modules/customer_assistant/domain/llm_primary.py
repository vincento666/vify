from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.core.config import Settings


class CustomerAssistantLlmRuntimeMode(StrEnum):
    DETERMINISTIC = "deterministic"
    SHADOW = "shadow"
    LLM_PRIMARY_WITH_FALLBACK = "llm_primary_with_fallback"
    TWO_STAGE_SHADOW = "two_stage_shadow"
    TWO_STAGE_PRIMARY_WITH_FALLBACK = "two_stage_primary_with_fallback"


@dataclass(frozen=True)
class CustomerAssistantLlmRuntimeSettings:
    mode: CustomerAssistantLlmRuntimeMode = CustomerAssistantLlmRuntimeMode.DETERMINISTIC
    model_config_id: int | None = None
    min_confidence: float = 0.70

    @classmethod
    def from_settings(cls, settings: Settings) -> CustomerAssistantLlmRuntimeSettings:
        raw_mode = str(settings.customer_assistant_llm_runtime_mode or "deterministic").strip().lower()
        try:
            mode = CustomerAssistantLlmRuntimeMode(raw_mode)
        except ValueError:
            mode = CustomerAssistantLlmRuntimeMode.DETERMINISTIC
        return cls(
            mode=mode,
            model_config_id=settings.customer_assistant_llm_primary_model_config_id,
            min_confidence=float(settings.customer_assistant_llm_primary_min_confidence),
        )
