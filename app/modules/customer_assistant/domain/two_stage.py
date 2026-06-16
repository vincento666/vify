from __future__ import annotations

from typing import Any, Protocol

from app.modules.customer_assistant.domain.models import AssistantTurnResult


TWO_STAGE_FINAL_SCHEMA_VERSION = "customer_assistant.two_stage_final/1"
TWO_STAGE_EQUIVALENCE_SUITE = "054-customer-assistant-synthetic-golden"
TWO_STAGE_EQUIVALENCE_MIN_PASS_RATE = 1.0


class TwoStageFinalizer(Protocol):
    def finalize(self, input_pack: dict[str, Any], baseline_result: AssistantTurnResult) -> dict[str, Any]:
        ...


class CustomerAssistantTwoStageRuntime:
    def finalize(self, input_pack: dict[str, Any], baseline_result: AssistantTurnResult) -> dict[str, Any]:
        del input_pack
        return {
            "schemaVersion": TWO_STAGE_FINAL_SCHEMA_VERSION,
            "operatorRecommendation": baseline_result.operator_recommendation,
            "customerReplyDraft": baseline_result.customer_reply_draft,
            "warnings": list(baseline_result.warnings),
        }
