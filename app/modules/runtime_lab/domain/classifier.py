from dataclasses import dataclass
from collections.abc import Callable, Mapping
from typing import Any

from app.modules.runtime_lab.domain.candidates import CandidateType, RouteCandidate, select_top_candidates

ALLOWED_ACTIONS = {
    "HANDOFF_TO_HUMAN",
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

    def to_llm_payload(self) -> dict[str, Any]:
        return {
            "message": self.message,
            "sessionState": _compact_session_state(self.session_state),
            "candidates": [_compact_candidate(candidate) for candidate in self.candidates],
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
    arbitrator_mode: str = "fake"
    used_real_llm: bool = False
    debug: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "selected_action": self.selected_action,
            "selected_candidate_id": self.selected_candidate_id,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "needs_clarification": self.needs_clarification,
            "clarification_question": self.clarification_question,
            "arbitrator_mode": self.arbitrator_mode,
            "used_real_llm": self.used_real_llm,
        }
        if self.debug:
            payload["_debug"] = self.debug
        return payload


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


class LlmConstrainedIntentClassifier:
    def __init__(self, complete: Callable[[dict[str, Any]], Mapping[str, Any]]) -> None:
        self._complete = complete

    def classify(self, classifier_input: ClassifierInput) -> ClassifierResult:
        raw = self._complete(classifier_input.to_llm_payload())
        result = ClassifierResult(
            selected_action=str(raw.get("selected_action") or ""),
            selected_candidate_id=_optional_string(raw.get("selected_candidate_id")),
            confidence=float(raw.get("confidence") or 0.0),
            rationale=str(raw.get("rationale") or "LLM constrained arbitrator selected from finite candidates"),
            needs_clarification=bool(raw.get("needs_clarification", False)),
            clarification_question=_optional_string(raw.get("clarification_question")),
            arbitrator_mode="llm",
            used_real_llm=True,
            debug=dict(raw.get("_debug")) if isinstance(raw.get("_debug"), Mapping) else None,
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
        clarification_question=(
            "请问您想办理订票、票价、团队票、增值服务、退票、改签、资料修改、发票、行李、"
            "值机、航班动态、特殊协助、宠物乘机、异常航班还是会员里程？"
        ),
    )


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _compact_session_state(session_state: Mapping[str, Any]) -> dict[str, Any]:
    allowed_keys = (
        "activeTask",
        "activeTaskId",
        "activeSopId",
        "activeStep",
        "suspendedTaskCount",
    )
    return {key: session_state[key] for key in allowed_keys if key in session_state}


def _compact_candidate(candidate: RouteCandidate) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "candidate_type": str(candidate.candidate_type),
        "name": candidate.display_name,
        "score": round(float(candidate.score), 3),
        "matched_terms": list(candidate.matched_terms[:3]),
        "requires_classifier": candidate.requires_classifier,
        "reason": _compact_reason(candidate),
    }


def _compact_reason(candidate: RouteCandidate) -> str:
    reason = str(candidate.reason or "")
    source = str(candidate.source or "")
    if "finite candidate fallback" in reason or "finite" in source:
        return "finite fallback"
    if "semantic" in source or "semantic" in reason.lower():
        return "semantic match"
    if "explicit" in source or "explicit" in reason.lower():
        return "explicit match"
    if "active" in source or str(candidate.candidate_type) == "ACTIVE_TASK_CONTINUE":
        return "active task candidate"
    if "suspended" in source or str(candidate.candidate_type) == "SUSPENDED_TASK_RESUME":
        return "suspended task candidate"
    return _compact_text(reason, max_chars=48)


def _compact_text(value: str, *, max_chars: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 1]}…"


def _action_for_candidate(candidate: RouteCandidate) -> str:
    candidate_type = CandidateType(str(candidate.candidate_type))
    if candidate_type == CandidateType.ACTIVE_TASK_CONTINUE:
        return "CONTINUE_ACTIVE_SOP"
    if candidate_type == CandidateType.SUSPENDED_TASK_RESUME:
        return "RESUME_TASK"
    if candidate_type == CandidateType.SOP_INTENT:
        return "START_SOP"
    if candidate_type == CandidateType.HANDOFF_TO_HUMAN:
        return "HANDOFF_TO_HUMAN"
    if candidate_type == CandidateType.REJECT_SWITCH_CONTINUE_ACTIVE:
        return "REJECT_SWITCH_CONTINUE_ACTIVE"
    return "CLARIFY"
