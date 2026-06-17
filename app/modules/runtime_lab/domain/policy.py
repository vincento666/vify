from collections.abc import Mapping, Sequence
from typing import Protocol
from typing import Any

from app.modules.runtime_lab.domain.candidates import CandidateType, RouteCandidate, select_top_candidates
from app.modules.runtime_lab.domain.classifier import ClassifierResult
from app.modules.runtime_lab.domain.router import RouteDecision


class InterruptibilityPolicy(Protocol):
    def is_interruptible(self, sop_id: str, step_id: str) -> bool:
        ...

STRONG_ACCEPT_THRESHOLD = 0.9


class PolicyGate:
    def __init__(
        self,
        adapter: InterruptibilityPolicy,
        *,
        strong_accept_threshold: float = STRONG_ACCEPT_THRESHOLD,
    ) -> None:
        self._adapter = adapter
        self._strong_accept_threshold = max(0.0, min(1.0, strong_accept_threshold))

    def pre_classifier_decision(
        self,
        candidates: Sequence[RouteCandidate],
        active_task: Mapping[str, Any] | None,
        suspended_count: int,
        *,
        allow_strong_sop_start: bool = False,
    ) -> RouteDecision | None:
        if not candidates:
            return None
        ordered = select_top_candidates(list(candidates), top_k=len(candidates))
        top = ordered[0]
        if _candidate_type(top) == CandidateType.HANDOFF_TO_HUMAN and top.score >= self._strong_accept_threshold:
            return _handoff_decision(top, "Explicit handoff candidate accepted before classifier")
        if (
            allow_strong_sop_start
            and active_task is None
            and _candidate_type(top) == CandidateType.SOP_INTENT
            and top.score >= self._strong_accept_threshold
            and not top.requires_classifier
            and not _has_conflicting_candidate(top, ordered)
        ):
            return RouteDecision(
                action="START_SOP",
                target_sop_id=top.target_id,
                matched_keyword=_matched_term(top),
                reason=f"Strong explicit SOP candidate accepted before classifier: {top.candidate_id}",
            )
        return None

    def classifier_decision(
        self,
        result: ClassifierResult,
        candidates: Sequence[RouteCandidate],
        active_task: Mapping[str, Any] | None,
        suspended_count: int,
    ) -> RouteDecision:
        if result.selected_action == "CLARIFY":
            candidate = _optional_candidate_by_id(candidates, result.selected_candidate_id)
            payload = dict(candidate.payload or {}) if candidate is not None else {}
            return RouteDecision(
                action="CLARIFY",
                reason=result.rationale,
                faq_answer=dict(payload.get("faq_answer") or {}),
                rag_answer=dict(payload.get("rag_answer") or {}),
                agent_answer=dict(payload.get("agent_answer") or {}),
            )
        candidate = _candidate_by_id(candidates, result.selected_candidate_id)
        candidate_type = _candidate_type(candidate)
        if candidate_type == CandidateType.HANDOFF_TO_HUMAN:
            return _handoff_decision(candidate, result.rationale)
        if candidate_type == CandidateType.ANSWER_FAQ:
            return RouteDecision(
                action="ANSWER_FAQ",
                reason=result.rationale,
                faq_answer=dict((candidate.payload or {}).get("faq_answer") or {}),
            )
        if candidate_type == CandidateType.ANSWER_RAG:
            return RouteDecision(
                action="ANSWER_RAG",
                reason=result.rationale,
                rag_answer=dict((candidate.payload or {}).get("rag_answer") or {}),
            )
        if candidate_type == CandidateType.AGENT_FALLBACK:
            return RouteDecision(
                action="AGENT_FALLBACK",
                reason=result.rationale,
                agent_answer=dict((candidate.payload or {}).get("agent_answer") or {}),
            )
        if candidate_type == CandidateType.ACTIVE_TASK_CONTINUE:
            return RouteDecision(
                action="CONTINUE_ACTIVE_SOP",
                active_task_id=int(candidate.target_id),
                reason=result.rationale,
            )
        if candidate_type == CandidateType.SUSPENDED_TASK_RESUME:
            if active_task is not None:
                active_collection = _active_collection_candidate(candidates)
                if active_collection is not None and active_collection.score >= candidate.score:
                    return RouteDecision(
                        action="CONTINUE_ACTIVE_SOP",
                        active_task_id=_active_task_id(active_task),
                        reason=(
                            "High-confidence active collection detail preserved over suspended resume; "
                            f"{result.rationale}"
                        ),
                    )
                return RouteDecision(
                    action="REJECT_SWITCH_SUSPENDED_LIMIT",
                    active_task_id=_active_task_id(active_task),
                    reason="Cannot resume suspended task while another task is active",
                )
            return RouteDecision(
                action="RESUME_TASK",
                active_task_id=int(candidate.target_id),
                reason=result.rationale,
            )
        if candidate_type == CandidateType.SOP_INTENT:
            active_collection = _active_collection_candidate(candidates)
            if active_task is not None and active_collection is not None and candidate.score < 0.75:
                return RouteDecision(
                    action="CONTINUE_ACTIVE_SOP",
                    active_task_id=_active_task_id(active_task),
                    reason=(
                        "High-confidence active collection detail preserved over weak classifier switch; "
                        f"{result.rationale}"
                    ),
                )
            if active_task is None:
                return RouteDecision(
                    action="START_SOP",
                    target_sop_id=candidate.target_id,
                    matched_keyword=_matched_term(candidate),
                    reason=result.rationale,
                )
            return self._switch_decision(candidate.target_id, active_task, suspended_count)
        if candidate_type == CandidateType.REJECT_SWITCH_CONTINUE_ACTIVE:
            return RouteDecision(
                action="REJECT_SWITCH_CONTINUE_ACTIVE",
                active_task_id=_active_task_id(active_task),
                reason=result.rationale,
            )
        return RouteDecision(action="CLARIFY", reason=result.rationale)

    def _switch_decision(
        self,
        target_sop_id: str,
        active_task: Mapping[str, Any],
        suspended_count: int,
    ) -> RouteDecision:
        active_sop_id = str(active_task.get("sop_id") or "")
        active_task_id = _active_task_id(active_task)
        if target_sop_id == active_sop_id:
            return RouteDecision(
                action="CONTINUE_ACTIVE_SOP",
                active_task_id=active_task_id,
                reason="Classifier selected active SOP",
            )
        if suspended_count >= 1:
            return RouteDecision(
                action="REJECT_SWITCH_SUSPENDED_LIMIT",
                target_sop_id=target_sop_id,
                active_task_id=active_task_id,
                reason="030 policy preserves max one suspended task",
            )
        if not self._adapter.is_interruptible(active_sop_id, str(active_task.get("current_step") or "")):
            return RouteDecision(
                action="REJECT_SWITCH_CONTINUE_ACTIVE",
                target_sop_id=target_sop_id,
                active_task_id=active_task_id,
                reason="Classifier selected switch from non-interruptible active step",
            )
        return RouteDecision(
            action="SUSPEND_AND_START",
            target_sop_id=target_sop_id,
            active_task_id=active_task_id,
            reason="Classifier selected different SOP at interruptible active step",
        )


def _candidate_by_id(candidates: Sequence[RouteCandidate], candidate_id: str | None) -> RouteCandidate:
    for candidate in candidates:
        if candidate.candidate_id == candidate_id:
            return candidate
    raise ValueError("Policy selected candidate outside finite candidate set")


def _optional_candidate_by_id(candidates: Sequence[RouteCandidate], candidate_id: str | None) -> RouteCandidate | None:
    if candidate_id is None:
        return None
    for candidate in candidates:
        if candidate.candidate_id == candidate_id:
            return candidate
    return None


def _active_collection_candidate(candidates: Sequence[RouteCandidate]) -> RouteCandidate | None:
    for candidate in candidates:
        if _candidate_type(candidate) == CandidateType.ACTIVE_TASK_CONTINUE and candidate.score >= 0.9:
            if "collection_detail" in candidate.matched_terms:
                return candidate
    return None


def _has_conflicting_candidate(
    top: RouteCandidate,
    ordered: Sequence[RouteCandidate],
) -> bool:
    for candidate in ordered[1:]:
        if _candidate_type(candidate) != CandidateType.SOP_INTENT:
            return True
        if candidate.target_id != top.target_id and candidate.score >= 0.75:
            return True
    return False


def _candidate_type(candidate: RouteCandidate) -> CandidateType:
    return CandidateType(str(candidate.candidate_type))


def _matched_term(candidate: RouteCandidate) -> str | None:
    return candidate.matched_terms[0] if candidate.matched_terms else None


def _active_task_id(active_task: Mapping[str, Any] | None) -> int | None:
    if active_task is None:
        return None
    raw = active_task.get("id")
    return int(raw) if raw is not None else None


def _handoff_decision(candidate: RouteCandidate, reason: str) -> RouteDecision:
    return RouteDecision(
        action="HANDOFF_TO_HUMAN",
        reason=reason,
        handoff={
            "sourceLayer": candidate.source or "system_policy",
            "reasonCode": candidate.target_id or "UNSPECIFIED",
            "matchedTerms": list(candidate.matched_terms),
            "routeEvidence": {
                "candidateId": candidate.candidate_id,
                "candidateType": str(candidate.candidate_type),
                "score": candidate.score,
                "riskLevel": candidate.risk_level,
                "reason": candidate.reason,
            },
        },
    )
