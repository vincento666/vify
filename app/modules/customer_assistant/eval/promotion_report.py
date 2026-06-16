from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from app.modules.customer_assistant.eval.runner import run_customer_assistant_eval
from app.modules.customer_assistant.eval.schemas import CustomerAssistantEvalCase


ReadinessStatus = Literal["ready", "mock_fallback", "missing_seed_data", "not_checked"]


@dataclass(frozen=True)
class ChatflowDataReadiness:
    status: ReadinessStatus = "not_checked"
    strategy: str = "not_checked"
    checked_sop_keys: list[str] = field(default_factory=list)
    missing_sop_keys: list[str] = field(default_factory=list)
    missing_chatflow_ids: list[int] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "strategy": self.strategy,
            "checkedSopKeys": self.checked_sop_keys,
            "missingSopKeys": self.missing_sop_keys,
            "missingChatflowIds": self.missing_chatflow_ids,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ShadowCandidateEvidence:
    case_id: str
    phase: str
    baseline: dict[str, Any]
    candidate: dict[str, Any]
    diff: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "caseId": self.case_id,
            "phase": self.phase,
            "baseline": self.baseline,
            "candidate": self.candidate,
            "diff": self.diff,
            "evidenceOnly": True,
        }


@dataclass(frozen=True)
class PromotionReport:
    total_cases: int
    task_recognition_pass_rate: float
    recommendation_pass_rate: float
    safety_pass_rate: float
    schema_failure_rate: float
    fallback_rate: float
    event_coverage_pass_rate: float
    live_model_calls: int
    chatflow_readiness: ChatflowDataReadiness
    shadow_candidates: list[ShadowCandidateEvidence]

    def to_dict(self) -> dict[str, Any]:
        return {
            "totalCases": self.total_cases,
            "taskRecognitionPassRate": self.task_recognition_pass_rate,
            "recommendationPassRate": self.recommendation_pass_rate,
            "safetyPassRate": self.safety_pass_rate,
            "schemaFailureRate": self.schema_failure_rate,
            "fallbackRate": self.fallback_rate,
            "eventCoveragePassRate": self.event_coverage_pass_rate,
            "liveModelCalls": self.live_model_calls,
            "chatflowDataReadiness": self.chatflow_readiness.to_dict(),
            "shadowCandidateDiffs": [candidate.to_dict() for candidate in self.shadow_candidates],
        }


def build_promotion_report(
    cases: list[CustomerAssistantEvalCase],
    *,
    chatflow_readiness: ChatflowDataReadiness | None = None,
    shadow_candidates: list[ShadowCandidateEvidence] | None = None,
    live_model_calls: int = 0,
) -> PromotionReport:
    base_report = run_customer_assistant_eval(cases)
    total = max(len(cases), 1)
    sections = base_report.sections
    return PromotionReport(
        total_cases=len(cases),
        task_recognition_pass_rate=_rate(sections["taskRecognition"].passed, total),
        recommendation_pass_rate=_rate(sections["recommendation"].passed, total),
        safety_pass_rate=_rate(sections["safety"].passed, total),
        schema_failure_rate=_case_rate(cases, "schema_failure"),
        fallback_rate=_case_rate(cases, "fallback_used"),
        event_coverage_pass_rate=_rate(_event_coverage_pass_count(cases), total),
        live_model_calls=live_model_calls,
        chatflow_readiness=chatflow_readiness or ChatflowDataReadiness(),
        shadow_candidates=shadow_candidates or [],
    )


def _rate(passed: int, total: int) -> float:
    return round(passed / total, 4)


def _case_rate(cases: list[CustomerAssistantEvalCase], metadata_key: str) -> float:
    total = max(len(cases), 1)
    count = sum(1 for case in cases if case.metadata.get(metadata_key))
    return _rate(count, total)


def _event_coverage_pass_count(cases: list[CustomerAssistantEvalCase]) -> int:
    passed = 0
    for case in cases:
        expected = set(case.metadata.get("expected_event_types", []))
        observed = set(case.metadata.get("observed_event_types", expected))
        if expected.issubset(observed):
            passed += 1
    return passed
