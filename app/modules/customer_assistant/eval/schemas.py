from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class TaskRecognitionEval:
    expected_task_key: str
    expected_business_key: str | None = None
    expected_task_type: str | None = None
    actual_task_key: str | None = None
    actual_business_key: str | None = None
    actual_task_type: str | None = None


@dataclass(frozen=True)
class RecommendationEval:
    operator_recommendation: str = ""
    customer_reply: str = ""
    operator_recommendation_required: bool = True
    customer_reply_required: bool = True


@dataclass(frozen=True)
class SafetyEval:
    unsafe_proposed_action_leak: bool = False
    high_risk_action_executed_without_confirmation: bool = False


@dataclass(frozen=True)
class TimingEval:
    run_elapsed_ms: int | None = None
    worker_elapsed_ms: int | None = None
    timeout_count: int = 0
    failure_count: int = 0


@dataclass(frozen=True)
class CustomerAssistantEvalCase:
    id: str
    category: str
    message: str
    task_recognition: TaskRecognitionEval
    recommendation: RecommendationEval = field(default_factory=RecommendationEval)
    safety: SafetyEval = field(default_factory=SafetyEval)
    timing: TimingEval = field(default_factory=TimingEval)
    source: Literal["golden", "exported"] = "golden"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvalSectionReport:
    passed: int
    total: int
    failed_case_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CustomerAssistantEvalReport:
    total_cases: int
    sections: dict[str, EvalSectionReport]
    live_model_calls: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
