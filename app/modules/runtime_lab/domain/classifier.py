from dataclasses import dataclass
from typing import Any

from app.modules.runtime_lab.domain.candidates import CandidateType, RouteCandidate, select_top_candidates

ALLOWED_ACTIONS = {
    "CONTINUE_ACTIVE_SOP",
    "START_SOP",
    "SUSPEND_AND_START",
    "RESUME_TASK",
    "CLARIFY",
    "REJECT_SWITCH_CONTINUE_ACTIVE",
}


@dataclass(frozen=True)
class ClassifierInput:
    message: str
    session_state: dict[str, Any]
    candidates: tuple[RouteCandidate, ...]
    allowed_actions: tuple[str, ...]
    thresholds: dict[str, float]

    def __post_init__(self) -> None:
        invalid_actions = set(self.allowed_actions) - ALLOWED_ACTIONS
        if invalid_actions:
            raise ValueError(f"Unsupported classifier actions: {sorted(invalid_actions)}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": self.message,
            "sessionState": self.session_state,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "allowedActions": list(self.allowed_actions),
            "thresholds": dict(self.thresholds),
        }


@dataclass(frozen=True)
class ClassifierResult:
    selected_action: str
    selected_candidate_id: str | None
    confidence: float
    rationale: str
    needs_clarification: bool
    clarification_question: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_action": self.selected_action,
            "selected_candidate_id": self.selected_candidate_id,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "needs_clarification": self.needs_clarification,
            "clarification_question": self.clarification_question,
        }


class FakeConstrainedIntentClassifier:
    def __init__(self, scripted_result: ClassifierResult | None = None) -> None:
        self._scripted_result = scripted_result

    def classify(self, classifier_input: ClassifierInput) -> ClassifierResult:
        if self._scripted_result is not None:
            result = self._scripted_result
            _validate_result(result, classifier_input)
            return result
        top = select_top_candidates(list(classifier_input.candidates), top_k=1)
        if not top:
            result = _clarify_result("No finite candidates")
            _validate_result(result, classifier_input)
            return result
        candidate = top[0]
        min_confidence = classifier_input.thresholds.get("classifierMinConfidence", 0.6)
        if candidate.score < min_confidence:
            result = _clarify_result("Top candidate below classifier minimum confidence")
            _validate_result(result, classifier_input)
            return result
        action = _action_for_candidate(candidate)
        if action not in classifier_input.allowed_actions:
            result = _clarify_result("Top candidate action is not allowed")
            _validate_result(result, classifier_input)
            return result
        result = ClassifierResult(
            selected_action=action,
            selected_candidate_id=candidate.candidate_id,
            confidence=candidate.score,
            rationale=f"Selected top finite candidate {candidate.candidate_id}",
            needs_clarification=False,
            clarification_question=None,
        )
        _validate_result(result, classifier_input)
        return result


def _validate_result(result: ClassifierResult, classifier_input: ClassifierInput) -> None:
    if result.selected_action not in ALLOWED_ACTIONS or result.selected_action not in classifier_input.allowed_actions:
        raise ValueError(f"Classifier selected unsupported action: {result.selected_action}")
    candidate_ids = {candidate.candidate_id for candidate in classifier_input.candidates}
    if result.selected_action != "CLARIFY" and result.selected_candidate_id not in candidate_ids:
        raise ValueError("Classifier selected candidate outside finite candidate set")


def _clarify_result(rationale: str) -> ClassifierResult:
    return ClassifierResult(
        selected_action="CLARIFY",
        selected_candidate_id=None,
        confidence=0.0,
        rationale=rationale,
        needs_clarification=True,
        clarification_question="请问您想办理退票、改签还是发票？",
    )


def _action_for_candidate(candidate: RouteCandidate) -> str:
    candidate_type = CandidateType(str(candidate.candidate_type))
    if candidate_type == CandidateType.ACTIVE_TASK_CONTINUE:
        return "CONTINUE_ACTIVE_SOP"
    if candidate_type == CandidateType.SUSPENDED_TASK_RESUME:
        return "RESUME_TASK"
    if candidate_type == CandidateType.SOP_INTENT:
        return "START_SOP"
    if candidate_type == CandidateType.REJECT_SWITCH_CONTINUE_ACTIVE:
        return "REJECT_SWITCH_CONTINUE_ACTIVE"
    return "CLARIFY"
