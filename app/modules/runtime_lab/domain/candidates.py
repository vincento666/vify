from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class CandidateType(StrEnum):
    ACTIVE_TASK_CONTINUE = "ACTIVE_TASK_CONTINUE"
    SUSPENDED_TASK_RESUME = "SUSPENDED_TASK_RESUME"
    SOP_INTENT = "SOP_INTENT"
    ANSWER_FAQ = "ANSWER_FAQ"
    ANSWER_RAG = "ANSWER_RAG"
    AGENT_FALLBACK = "AGENT_FALLBACK"
    HANDOFF_TO_HUMAN = "HANDOFF_TO_HUMAN"
    CLARIFY = "CLARIFY"
    REJECT_SWITCH_CONTINUE_ACTIVE = "REJECT_SWITCH_CONTINUE_ACTIVE"


@dataclass(frozen=True)
class ScoreBreakdown:
    keyword: float
    alias: float
    semantic: float

    def to_dict(self) -> dict[str, float]:
        return {
            "keyword": self.keyword,
            "alias": self.alias,
            "semantic": self.semantic,
        }


@dataclass(frozen=True)
class RouteCandidate:
    candidate_id: str
    candidate_type: CandidateType | str
    target_id: str
    display_name: str
    source: str
    score: float
    score_breakdown: ScoreBreakdown
    matched_terms: tuple[str, ...]
    risk_level: str
    requires_classifier: bool
    reason: str
    payload: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_type, CandidateType):
            object.__setattr__(self, "candidate_type", CandidateType(str(self.candidate_type)))

    def to_dict(self) -> dict[str, Any]:
        candidate_type = _candidate_type(self.candidate_type)
        payload = {
            "candidate_id": self.candidate_id,
            "candidate_type": candidate_type.value,
            "target_id": self.target_id,
            "display_name": self.display_name,
            "source": self.source,
            "score": self.score,
            "score_breakdown": self.score_breakdown.to_dict(),
            "matched_terms": list(self.matched_terms),
            "risk_level": self.risk_level,
            "requires_classifier": self.requires_classifier,
            "reason": self.reason,
        }
        if self.payload:
            payload["payload"] = dict(self.payload)
        return payload


def select_top_candidates(candidates: list[RouteCandidate], top_k: int) -> list[RouteCandidate]:
    if top_k <= 0:
        return []
    indexed = enumerate(candidates)
    ordered = sorted(indexed, key=lambda item: (-item[1].score, item[0]))
    return [candidate for _, candidate in ordered[:top_k]]


def _candidate_type(value: CandidateType | str) -> CandidateType:
    if isinstance(value, CandidateType):
        return value
    return CandidateType(str(value))
