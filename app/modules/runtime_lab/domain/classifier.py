from dataclasses import dataclass
from collections.abc import Callable, Mapping
import math
import re
from typing import Any

from app.modules.runtime_lab.domain.candidates import CandidateType, RouteCandidate, select_top_candidates

ALLOWED_ACTIONS = {
    "ANSWER_FAQ",
    "ANSWER_RAG",
    "AGENT_FALLBACK",
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
        payload: dict[str, Any] = {
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


class UncertaintyPolicy:
    def enforce(
        self,
        result: ClassifierResult,
        classifier_input: ClassifierInput,
    ) -> ClassifierResult:
        try:
            confidence = float(result.confidence)
        except (TypeError, ValueError):
            confidence = math.nan
        minimum = _minimum_confidence(classifier_input)
        candidate_ids = {candidate.candidate_id for candidate in classifier_input.candidates}
        incoherent = (
            result.selected_action not in classifier_input.allowed_actions
            or result.selected_action not in ALLOWED_ACTIONS
            or (
                result.selected_action != "CLARIFY"
                and result.selected_candidate_id not in candidate_ids
            )
            or (result.selected_action == "CLARIFY" and not result.needs_clarification)
        )
        reason = next(
            (
                value
                for condition, value in (
                    (result.needs_clarification, "Classifier requested clarification"),
                    (not math.isfinite(confidence), "Classifier confidence is not finite"),
                    (confidence < 0.0 or confidence > 1.0, "Classifier confidence is outside 0..1"),
                    (confidence < minimum, "Classifier confidence is below the configured minimum"),
                    (incoherent, "Classifier result is incoherent"),
                )
                if condition
            ),
            None,
        )
        if reason is None:
            return result
        fallback = _clarify_result(reason)
        question = _normalized_question(result.clarification_question)
        clarification_candidate_id = (
            result.selected_candidate_id
            if result.selected_action == "CLARIFY" and result.selected_candidate_id in candidate_ids
            else None
        )
        return ClassifierResult(
            selected_action=fallback.selected_action,
            selected_candidate_id=clarification_candidate_id,
            confidence=0.0,
            rationale=f"{reason}; {result.rationale}",
            needs_clarification=True,
            clarification_question=question or fallback.clarification_question,
            arbitrator_mode=result.arbitrator_mode,
            used_real_llm=result.used_real_llm,
            debug=dict(result.debug or {}),
        )


class FakeConstrainedIntentClassifier:
    def __init__(self, scripted_result: ClassifierResult | None = None) -> None:
        self._scripted_result = scripted_result

    def classify(self, classifier_input: ClassifierInput) -> ClassifierResult:
        if self._scripted_result is not None:
            result = self._scripted_result
            _validate_result(result, classifier_input)
            return result
        candidates = list(classifier_input.candidates)
        top = select_top_candidates(candidates, top_k=1)
        if not top:
            result = _clarify_result("No finite candidates")
            _validate_result(result, classifier_input)
            return result
        min_confidence = classifier_input.thresholds.get("classifierMinConfidence", 0.6)
        candidate = _preferred_fake_candidate(
            classifier_input.message,
            candidates,
            min_confidence,
        ) or _source_evidence_tie_break(top[0], candidates)
        candidate_type = CandidateType(str(candidate.candidate_type))
        if candidate.score < min_confidence and candidate_type not in {
            CandidateType.CLARIFY,
            CandidateType.ACTIVE_TASK_CONTINUE,
        }:
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
            confidence=max(
                min_confidence if candidate_type == CandidateType.ACTIVE_TASK_CONTINUE else 0.0,
                min(1.0, candidate.score),
            ),
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
        raw_debug = raw.get("_debug")
        debug = dict(raw_debug) if isinstance(raw_debug, Mapping) else None
        result = ClassifierResult(
            selected_action=str(raw.get("selected_action") or ""),
            selected_candidate_id=_optional_string(raw.get("selected_candidate_id")),
            confidence=_parsed_confidence(raw.get("confidence")),
            rationale=str(raw.get("rationale") or "LLM constrained arbitrator selected from finite candidates"),
            needs_clarification=bool(raw.get("needs_clarification", False)),
            clarification_question=_optional_string(raw.get("clarification_question")),
            arbitrator_mode="llm",
            used_real_llm=True,
            debug=debug,
        )
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


def _minimum_confidence(classifier_input: ClassifierInput) -> float:
    value = classifier_input.thresholds.get("classifierMinConfidence", 0.6)
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.6
    if not math.isfinite(parsed):
        return 0.6
    return max(0.0, min(1.0, parsed))


def _parsed_confidence(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return math.nan


def _normalized_question(value: object) -> str | None:
    if value is None:
        return None
    normalized = " ".join(str(value).split()).strip()
    if not normalized:
        return None
    return normalized[:256].rstrip()


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


def _preferred_fake_candidate(
    message: str,
    candidates: list[RouteCandidate],
    min_confidence: float,
) -> RouteCandidate | None:
    resume_candidates = [
        candidate
        for candidate in candidates
        if CandidateType(str(candidate.candidate_type)) == CandidateType.SUSPENDED_TASK_RESUME
        and candidate.score >= min_confidence
    ]
    if resume_candidates and _looks_like_resume_request(message):
        return select_top_candidates(resume_candidates, top_k=1)[0]
    active_continue = next(
        (candidate for candidate in candidates if CandidateType(str(candidate.candidate_type)) == CandidateType.ACTIVE_TASK_CONTINUE),
        None,
    )
    if _looks_like_consultation(message):
        answer_candidates = [
            candidate
            for candidate in candidates
            if CandidateType(str(candidate.candidate_type)) in {CandidateType.ANSWER_FAQ, CandidateType.ANSWER_RAG}
            and candidate.score >= min_confidence
        ]
        if answer_candidates:
            return select_top_candidates(answer_candidates, top_k=1)[0]
        clarify_answer_candidates = [
            candidate
            for candidate in candidates
            if CandidateType(str(candidate.candidate_type)) == CandidateType.CLARIFY
            and _has_answer_payload(candidate)
        ]
        if clarify_answer_candidates:
            return select_top_candidates(clarify_answer_candidates, top_k=1)[0]
    if active_continue is not None and _looks_like_active_collection_detail(message):
        sop_candidates = [
            candidate
            for candidate in candidates
            if CandidateType(str(candidate.candidate_type)) == CandidateType.SOP_INTENT
            and candidate.score >= min_confidence
        ]
        if sop_candidates and _looks_like_sop_transaction(message):
            return select_top_candidates(sop_candidates, top_k=1)[0]
        return active_continue
    return None


def _source_evidence_tie_break(
    top: RouteCandidate,
    candidates: list[RouteCandidate],
) -> RouteCandidate:
    tied = [candidate for candidate in candidates if candidate.score == top.score]
    if len(tied) < 2:
        return top
    return min(
        tied,
        key=lambda candidate: (
            -_highest_raw_source_score(candidate),
            candidate.canonical_key,
            candidate.candidate_id,
        ),
    )


def _highest_raw_source_score(candidate: RouteCandidate) -> float:
    scores: list[float] = []
    for observation in candidate.source_evidence:
        try:
            scores.append(float(observation["rawScore"]))
        except (KeyError, TypeError, ValueError):
            continue
    return max(scores, default=float(candidate.score))


def _looks_like_consultation(message: str) -> bool:
    return any(term in message for term in ("?", "？", "吗", "怎么", "如何", "赔", "规则", "手续费", "多少", "能不能"))


def _looks_like_resume_request(message: str) -> bool:
    return any(term in message for term in ("继续", "恢复", "接着", "刚才", "之前", "刚订", "刚出票", "就查"))


def _looks_like_sop_transaction(message: str) -> bool:
    action_terms = ("我要", "我想", "帮我", "办理", "申请", "提交", "先帮我", "先不")
    sop_terms = (
        "退票",
        "退款",
        "退费",
        "改签",
        "订票",
        "机票",
        "开发票",
        "开票",
        "加购",
        "行李",
        "值机",
        "选座",
    )
    return any(term in message for term in action_terms) and any(term in message for term in sop_terms)


def _looks_like_active_collection_detail(message: str) -> bool:
    return bool(re.search(r"[A-Za-z]{2,}-?\d{2,}|\d{6,}|1[3-9]\d{9}", message)) or any(
        term in message for term in ("订单", "票号", "手机号", "证件", "身份证", "护照", "乘机人", "确认")
    )


def _has_answer_payload(candidate: RouteCandidate) -> bool:
    payload = candidate.payload or {}
    return bool(payload.get("faq_answer") or payload.get("rag_answer"))


def _action_for_candidate(candidate: RouteCandidate) -> str:
    candidate_type = CandidateType(str(candidate.candidate_type))
    if candidate_type == CandidateType.ACTIVE_TASK_CONTINUE:
        return "CONTINUE_ACTIVE_SOP"
    if candidate_type == CandidateType.SUSPENDED_TASK_RESUME:
        return "RESUME_TASK"
    if candidate_type == CandidateType.SOP_INTENT:
        return "START_SOP"
    if candidate_type == CandidateType.ANSWER_FAQ:
        return "ANSWER_FAQ"
    if candidate_type == CandidateType.ANSWER_RAG:
        return "ANSWER_RAG"
    if candidate_type == CandidateType.AGENT_FALLBACK:
        return "AGENT_FALLBACK"
    if candidate_type == CandidateType.HANDOFF_TO_HUMAN:
        return "HANDOFF_TO_HUMAN"
    if candidate_type == CandidateType.REJECT_SWITCH_CONTINUE_ACTIVE:
        return "REJECT_SWITCH_CONTINUE_ACTIVE"
    return "CLARIFY"
