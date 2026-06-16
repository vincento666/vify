import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from time import perf_counter
from typing import Any, Protocol

from app.core.errors import BizError, ErrorCode
from app.modules.runtime_lab.domain.agent_fallback import AgentOutputPolicy, FallbackAgentPort, FallbackAgentRequest
from app.modules.runtime_lab.domain.candidates import RouteCandidate, ScoreBreakdown, select_top_candidates
from app.modules.runtime_lab.domain.classifier import ClassifierInput, ClassifierResult, FakeConstrainedIntentClassifier
from app.modules.runtime_lab.domain.explicit_signals import ExplicitSignalDetector
from app.modules.runtime_lab.domain.faq_gate import FaqAnswerGate, FaqSemanticAnswerGate
from app.modules.runtime_lab.domain.payload import format_turn
from app.modules.runtime_lab.domain.policy import PolicyGate
from app.modules.runtime_lab.domain.rag_gate import RagAnswerGate
from app.modules.runtime_lab.domain.recall import MockSemanticCandidateRecall
from app.modules.runtime_lab.domain.router import RouteDecision, RuntimeLabRouter
from app.modules.runtime_lab.domain.sop import mock_sop_manifests
from app.modules.runtime_lab.domain.sop_adapter import (
    FakeSopRuntimeAdapter,
    SopCheckpoint,
    SopExecutionRequest,
    SopExecutionResult,
    SopExecutionStatus,
    SopRuntimeAdapter,
)
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository


@dataclass(frozen=True)
class RuntimeLabTurn:
    reply: str
    route_decision: RouteDecision
    active_task: dict[str, Any] | None
    suspended_tasks: list[dict[str, Any]]
    resume_offer: dict[str, Any] | None
    events: list[dict[str, Any]]


@dataclass(frozen=True)
class RuntimeLabCommandResult:
    payload: dict[str, Any]
    replayed: bool


class HandoffRuntimeService(Protocol):
    def create_ticket(self, data: dict[str, Any]) -> dict[str, Any]:
        ...


class RuntimeLabService:
    def __init__(
        self,
        repository: RuntimeLabRepository,
        router: RuntimeLabRouter | None = None,
        adapter: SopRuntimeAdapter | None = None,
        classifier: Any | None = None,
        handoff_service: HandoffRuntimeService | None = None,
        faq_answer_gate: FaqAnswerGate | None = None,
        faq_semantic_gate: FaqSemanticAnswerGate | None = None,
        rag_answer_gate: RagAnswerGate | None = None,
        fallback_agent: FallbackAgentPort | None = None,
        agent_output_policy: AgentOutputPolicy | None = None,
        policy_thresholds: dict[str, Any] | None = None,
    ) -> None:
        self._repository = repository
        self._manifests = mock_sop_manifests()
        self._adapter = adapter or FakeSopRuntimeAdapter()
        self._router = router or RuntimeLabRouter(self._adapter)
        self._explicit_signals = ExplicitSignalDetector(self._manifests)
        self._semantic_recall = MockSemanticCandidateRecall(self._manifests)
        self._classifier = classifier or FakeConstrainedIntentClassifier()
        self._policy_thresholds = dict(policy_thresholds or {})
        self._policy_gate = PolicyGate(
            self._adapter,
            strong_accept_threshold=self._strong_accept_threshold(),
        )
        self._handoff_service = handoff_service
        self._faq_answer_gate = faq_answer_gate
        self._faq_semantic_gate = faq_semantic_gate
        self._rag_answer_gate = rag_answer_gate
        self._fallback_agent = fallback_agent
        self._agent_output_policy = agent_output_policy or AgentOutputPolicy()

    def create_session(self) -> dict[str, Any]:
        runtime_session = self._repository.create_session()
        self._repository.append_event(int(runtime_session["id"]), "SESSION_CREATED", {})
        return runtime_session

    def handle_message(
        self,
        session_id: int,
        message: str,
        enabled_sop_ids: Sequence[str] | None = None,
    ) -> RuntimeLabTurn:
        self._ensure_session_exists(session_id)
        self._repository.append_event(session_id, "USER_MESSAGE", {"message": message})
        active_task = self._repository.get_active_task(session_id)
        suspended_tasks = self._repository.list_tasks(session_id, statuses={"SUSPENDED"})
        enabled_scope = self._normalize_enabled_sop_ids(enabled_sop_ids)
        decision = self._semantic_decision(session_id, message, active_task, suspended_tasks, enabled_scope)
        self._repository.append_event(session_id, "ROUTE_DECISION", _decision_payload(decision))

        if decision.action == "HANDOFF_TO_HUMAN":
            return self._handoff_turn(session_id, message, decision)

        if decision.action == "ANSWER_FAQ":
            return self._faq_turn(session_id, decision)

        if decision.action == "ANSWER_RAG":
            return self._rag_turn(session_id, decision)

        if decision.action == "AGENT_FALLBACK":
            return self._agent_fallback_turn(session_id, message, active_task, suspended_tasks, decision)

        if decision.action == "START_SOP" and decision.target_sop_id is not None:
            result = self._adapter.start_sop(
                self._adapter_request(
                    session_id,
                    decision.target_sop_id,
                    message=message,
                    collected=self._session_business_context(session_id),
                )
            )
            if result.status == SopExecutionStatus.FAILED:
                return self._adapter_failure_turn(session_id, result, decision)
            task = self._start_task(session_id, decision.target_sop_id, result)
            self._repository.append_event(
                session_id,
                "TASK_STARTED",
                {"taskId": task["id"], "sopId": task["sop_id"]},
            )
            return self._turn(session_id, result.reply, decision)

        if decision.action == "SUSPEND_AND_START" and active_task is not None and decision.target_sop_id is not None:
            suspended = self._suspend_task(session_id, active_task)
            self._repository.append_event(
                session_id,
                "TASK_SUSPENDED",
                {"taskId": suspended["id"], "sopId": suspended["sop_id"]},
            )
            result = self._adapter.start_sop(
                self._adapter_request(
                    session_id,
                    decision.target_sop_id,
                    message=message,
                    collected=self._session_business_context(session_id),
                )
            )
            if result.status == SopExecutionStatus.FAILED:
                return self._adapter_failure_turn(session_id, result, decision)
            task = self._start_task(session_id, decision.target_sop_id, result)
            self._repository.append_event(
                session_id,
                "TASK_STARTED",
                {"taskId": task["id"], "sopId": task["sop_id"]},
            )
            return self._turn(session_id, result.reply, decision)

        if decision.action in {"REJECT_SWITCH_CONTINUE_ACTIVE", "REJECT_SWITCH_SUSPENDED_LIMIT"}:
            self._repository.append_event(session_id, "SWITCH_REJECTED", _decision_payload(decision))
            if decision.action == "REJECT_SWITCH_SUSPENDED_LIMIT":
                return self._turn(session_id, "当前已有一个暂停流程，请先完成或恢复后再切换。", decision)
            return self._turn(session_id, "当前步骤不能中断，请先完成确认后再切换。", decision)

        if decision.action == "RESUME_TASK":
            return self._resume_task(session_id, decision, message)

        if decision.action == "CLARIFY":
            if decision.agent_answer:
                return self._agent_clarify_turn(session_id, decision)
            return self._turn(
                session_id,
                "请问您想办理订票、票价、团队票、增值服务、退票、改签、资料修改、发票、行李、"
                "值机、航班动态、特殊协助、宠物乘机、异常航班还是会员里程？",
                decision,
            )

        if decision.action == "CONTINUE_ACTIVE_SOP" and active_task is not None:
            return self._continue_active_task(session_id, active_task, message, decision)

        return self._turn(session_id, "暂未匹配到可执行的航空业务流程。", decision)

    def handle_command(
        self,
        session_id: int,
        message: str,
        idempotency_key: str | None = None,
        enabled_sop_ids: Sequence[str] | None = None,
        policy_thresholds_override: Mapping[str, Any] | None = None,
        classifier_override: Any | None = None,
        route_settings_signature: Mapping[str, Any] | None = None,
    ) -> RuntimeLabCommandResult:
        self._ensure_session_exists(session_id)
        normalized_thresholds_override = _normalized_policy_thresholds_override(policy_thresholds_override)
        request_hash = _request_hash(
            message,
            enabled_sop_ids,
            normalized_thresholds_override,
            route_settings_signature,
        )
        if idempotency_key:
            existing = self._repository.get_command_response(session_id, idempotency_key)
            if existing is not None:
                if existing["request_hash"] != request_hash:
                    raise BizError(ErrorCode.BAD_REQUEST, "Idempotency key reused with different request")
                return RuntimeLabCommandResult(dict(existing["response_payload"]), replayed=True)
        previous_thresholds = self._policy_thresholds
        previous_policy_gate = self._policy_gate
        previous_classifier = self._classifier
        if normalized_thresholds_override:
            self._policy_thresholds = {**previous_thresholds, **normalized_thresholds_override}
            self._policy_gate = PolicyGate(
                self._adapter,
                strong_accept_threshold=self._strong_accept_threshold(),
            )
        if classifier_override is not None:
            self._classifier = classifier_override
        try:
            payload = format_turn(self.handle_message(session_id, message, enabled_sop_ids=enabled_sop_ids))
        finally:
            self._policy_thresholds = previous_thresholds
            self._policy_gate = previous_policy_gate
            self._classifier = previous_classifier
        if idempotency_key:
            self._repository.store_command_response(session_id, idempotency_key, request_hash, payload)
        return RuntimeLabCommandResult(payload, replayed=False)

    def list_tasks(self, session_id: int) -> list[dict[str, Any]]:
        return self._repository.list_tasks(session_id)

    def list_events(self, session_id: int) -> list[dict[str, Any]]:
        return self._repository.list_events(session_id)

    def _classifier_min_confidence(self) -> float:
        value = self._policy_thresholds.get("classifierMinConfidence", 0.6)
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return 0.6
        return max(0.0, min(1.0, parsed))

    def _strong_accept_threshold(self) -> float:
        value = self._policy_thresholds.get("strongAcceptThreshold", 0.9)
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return 0.9
        return max(0.0, min(1.0, parsed))

    def _candidate_top_k(self) -> int:
        value = self._policy_thresholds.get("candidateTopK", 5)
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return 5
        return max(1, min(20, parsed))

    def _candidate_source_weights(self) -> dict[str, float]:
        raw = self._policy_thresholds.get("candidateSourceWeights")
        if not isinstance(raw, dict):
            return {}
        weights: dict[str, float] = {}
        for key, value in raw.items():
            text = str(key).strip()
            if not text:
                continue
            try:
                weights[text] = max(0.0, min(5.0, float(value)))
            except (TypeError, ValueError):
                continue
        return weights

    def _select_top_candidates(
        self,
        candidates: list[RouteCandidate],
        *,
        top_k: int | None = None,
    ) -> list[RouteCandidate]:
        weighted = self._apply_candidate_source_weights(candidates)
        return select_top_candidates(weighted, top_k=top_k or self._candidate_top_k())

    def _apply_candidate_source_weights(self, candidates: list[RouteCandidate]) -> list[RouteCandidate]:
        weights = self._candidate_source_weights()
        if not weights:
            return candidates
        weighted: list[RouteCandidate] = []
        for candidate in candidates:
            weight = weights.get(str(candidate.candidate_type), weights.get(str(candidate.source), weights.get("*", 1.0)))
            if weight == 1.0:
                weighted.append(candidate)
                continue
            payload = dict(candidate.payload or {})
            payload["policyWeight"] = {
                "rawScore": candidate.score,
                "sourceWeight": weight,
                "weightedScore": max(0.0, min(1.0, candidate.score * weight)),
            }
            weighted.append(
                replace(
                    candidate,
                    score=max(0.0, min(1.0, candidate.score * weight)),
                    payload=payload,
                )
            )
        return weighted

    def get_command_response(self, session_id: int, idempotency_key: str) -> dict[str, Any] | None:
        return self._repository.get_command_response(session_id, idempotency_key)

    def store_command_response(
        self,
        session_id: int,
        idempotency_key: str,
        request_hash: str,
        response_payload: dict[str, Any],
    ) -> None:
        self._repository.store_command_response(session_id, idempotency_key, request_hash, response_payload)

    def _semantic_decision(
        self,
        session_id: int,
        message: str,
        active_task: dict[str, Any] | None,
        suspended_tasks: list[dict[str, Any]],
        enabled_sop_ids: frozenset[str] | None,
    ) -> RouteDecision:
        route_started_at = perf_counter()
        route_steps: list[dict[str, Any]] = []
        step_started_at = perf_counter()
        hard_stop_candidates = self._explicit_signals.detect(
            message,
            active_task=active_task,
            suspended_tasks=suspended_tasks,
            enabled_sop_ids=enabled_sop_ids,
        )
        hard_stop_decision = self._policy_gate.pre_classifier_decision(
            hard_stop_candidates,
            active_task,
            len(suspended_tasks),
        )
        if hard_stop_decision is not None and hard_stop_decision.action == "HANDOFF_TO_HUMAN":
            route_steps.append(
                _route_step(
                    "hard_stop_policy",
                    step_started_at,
                    {"message": message, "activeTask": active_task is not None},
                    {"decision": _decision_payload(hard_stop_decision)},
                )
            )
            return _with_evidence(
                hard_stop_decision,
                hard_stop_candidates,
                "explicit_signal",
                route_steps=route_steps,
                route_elapsed_ms=_elapsed_ms(route_started_at),
            )
        step_started_at = perf_counter()
        candidates = self._route_candidates(message, active_task, suspended_tasks, enabled_sop_ids)
        route_steps.append(
            _route_step(
                "candidate_recall",
                step_started_at,
                {"message": message, "enabledSopIds": sorted(enabled_sop_ids) if enabled_sop_ids is not None else None},
                {"candidateCount": len(candidates), "candidates": [candidate.to_dict() for candidate in candidates]},
            )
        )
        duplicate_confirmation = self._recent_completed_confirmation_decision(session_id, message, active_task, suspended_tasks)
        if duplicate_confirmation is not None:
            route_steps.append(
                _route_step(
                    "recent_completed_guard",
                    perf_counter(),
                    {"message": message},
                    {"decision": _decision_payload(duplicate_confirmation)},
                )
            )
            return _with_evidence(
                duplicate_confirmation,
                candidates,
                "recent_completed_guard",
                route_steps=route_steps,
                route_elapsed_ms=_elapsed_ms(route_started_at),
            )
        hard_stop_decision = self._policy_gate.pre_classifier_decision(candidates, active_task, len(suspended_tasks))
        if hard_stop_decision is not None and hard_stop_decision.action == "HANDOFF_TO_HUMAN":
            route_steps.append(
                _route_step(
                    "hard_stop_policy",
                    perf_counter(),
                    {"activeTask": active_task is not None, "suspendedTaskCount": len(suspended_tasks)},
                    {"decision": _decision_payload(hard_stop_decision)},
                )
            )
            return _with_evidence(
                hard_stop_decision,
                candidates,
                "explicit_signal",
                route_steps=route_steps,
                route_elapsed_ms=_elapsed_ms(route_started_at),
            )
        if not candidates:
            step_started_at = perf_counter()
            if enabled_sop_ids is not None and not enabled_sop_ids:
                candidates = self._agent_fallback_candidates(message, reason="No enabled SOP candidate matched")
                if candidates:
                    route_steps.append(
                        _route_step(
                            "agent_candidate_recall",
                            step_started_at,
                            {"message": message, "enabledSopIds": []},
                            {"candidateCount": len(candidates), "candidates": [candidate.to_dict() for candidate in candidates]},
                        )
                    )
                else:
                    route_steps.append(
                        _route_step(
                            "enabled_scope",
                            step_started_at,
                            {"message": message, "enabledSopIds": []},
                            {"reason": "No enabled SOP candidate matched"},
                        )
                    )
                    return _with_evidence(
                        RouteDecision(action="NO_MATCH", reason="No enabled SOP candidate matched"),
                        (),
                        "enabled_scope",
                        route_steps=route_steps,
                        route_elapsed_ms=_elapsed_ms(route_started_at),
                    )
            else:
                candidates = self._scoped_finite_fallback_candidates(message, enabled_sop_ids)
                if candidates:
                    route_steps.append(
                        _route_step(
                            "scoped_finite_fallback",
                            step_started_at,
                            {
                                "message": message,
                                "enabledSopIds": sorted(enabled_sop_ids) if enabled_sop_ids is not None else None,
                            },
                            {"candidateCount": len(candidates), "candidates": [candidate.to_dict() for candidate in candidates]},
                        )
                    )
                else:
                    candidates = self._agent_fallback_candidates(message, reason="No shallow or scoped finite route signal")
                    if candidates:
                        route_steps.append(
                            _route_step(
                                "agent_candidate_recall",
                                step_started_at,
                                {
                                    "message": message,
                                    "enabledSopIds": sorted(enabled_sop_ids) if enabled_sop_ids is not None else None,
                                },
                                {"candidateCount": len(candidates), "candidates": [candidate.to_dict() for candidate in candidates]},
                            )
                        )
                    else:
                        route_steps.append(
                            _route_step(
                                "no_signal_clarify",
                                step_started_at,
                                {
                                    "message": message,
                                    "enabledSopIds": sorted(enabled_sop_ids) if enabled_sop_ids is not None else None,
                                },
                                {"reason": "No shallow or scoped finite route signal"},
                            )
                        )
                        return _with_evidence(
                            RouteDecision(action="CLARIFY", reason="No shallow or scoped finite route signal"),
                            (),
                            "no_signal_clarify",
                            route_steps=route_steps,
                            route_elapsed_ms=_elapsed_ms(route_started_at),
                        )
        if _should_agent_fallback_before_active_continue(candidates, active_task, message):
            agent_candidates = self._agent_fallback_candidates(
                message,
                reason="Fallback Agent candidate added for non-SOP question during active task",
            )
            if agent_candidates:
                candidates = self._select_top_candidates([*candidates, *agent_candidates])
                route_steps.append(
                    _route_step(
                        "agent_candidate_recall",
                        perf_counter(),
                        {"message": message, "activeTask": active_task is not None},
                        {"candidateCount": len(candidates), "candidates": [candidate.to_dict() for candidate in candidates]},
                    )
                )
        step_started_at = perf_counter()
        pre_decision = self._policy_gate.pre_classifier_decision(candidates, active_task, len(suspended_tasks))
        route_steps.append(
            _route_step(
                "pre_classifier_policy",
                step_started_at,
                {"activeTask": active_task is not None, "suspendedTaskCount": len(suspended_tasks)},
                {"decision": _decision_payload(pre_decision) if pre_decision is not None else None},
            )
        )
        if pre_decision is not None:
            return _with_evidence(
                pre_decision,
                candidates,
                "pre_classifier",
                route_steps=route_steps,
                route_elapsed_ms=_elapsed_ms(route_started_at),
            )
        classifier_input = ClassifierInput(
            message=message,
            session_state={
                "activeTask": active_task is not None,
                "suspendedTaskCount": len(suspended_tasks),
                "enabledSopIds": sorted(enabled_sop_ids) if enabled_sop_ids is not None else None,
            },
            candidates=tuple(candidates),
            allowed_actions=(
                "CONTINUE_ACTIVE_SOP",
                "START_SOP",
                "SUSPEND_AND_START",
                "RESUME_TASK",
                "CLARIFY",
                "REJECT_SWITCH_CONTINUE_ACTIVE",
                "ANSWER_FAQ",
                "ANSWER_RAG",
                "AGENT_FALLBACK",
            ),
            thresholds={"classifierMinConfidence": self._classifier_min_confidence()},
        )
        step_started_at = perf_counter()
        try:
            classifier_result = self._classifier.classify(classifier_input)
        except Exception as exc:
            classifier_result = _classifier_failure_result(exc, self._classifier, classifier_input)
        classifier_result = _recover_clarify_result(classifier_result, candidates, message, active_task)
        route_steps.append(
            _route_step(
                "llm_intent_arbitration",
                step_started_at,
                classifier_input.to_llm_payload(),
                classifier_result.to_dict(),
            )
        )
        step_started_at = perf_counter()
        decision = self._policy_gate.classifier_decision(classifier_result, candidates, active_task, len(suspended_tasks))
        route_steps.append(
            _route_step(
                "post_classifier_policy",
                step_started_at,
                classifier_result.to_dict(),
                _decision_payload(decision),
            )
        )
        return _with_evidence(
            decision,
            candidates,
            "post_classifier",
            classifier_input,
            classifier_result,
            route_steps=route_steps,
            route_elapsed_ms=_elapsed_ms(route_started_at),
        )

    def _route_candidates(
        self,
        message: str,
        active_task: dict[str, Any] | None,
        suspended_tasks: list[dict[str, Any]],
        enabled_sop_ids: frozenset[str] | None,
    ) -> list[RouteCandidate]:
        candidates = [
            *self._explicit_signals.detect(
                message,
                active_task=active_task,
                suspended_tasks=suspended_tasks,
                enabled_sop_ids=enabled_sop_ids,
            ),
            *self._semantic_recall.recall(
                message,
                active_task=active_task,
                suspended_tasks=suspended_tasks,
                enabled_sop_ids=enabled_sop_ids,
            ),
            *self._faq_answer_candidates(
                message,
                active_task=active_task,
                suspended_tasks=suspended_tasks,
            ),
            *self._faq_semantic_candidates(
                message,
                active_task=active_task,
                suspended_tasks=suspended_tasks,
            ),
            *self._rag_answer_candidates(
                message,
                active_task=active_task,
                suspended_tasks=suspended_tasks,
            ),
        ]
        if _should_add_agent_fallback_candidate(candidates, active_task, message):
            candidates.extend(
                self._agent_fallback_candidates(
                    message,
                    reason="Fallback Agent candidate added to unresolved answer candidate pool",
                )
            )
        return self._select_top_candidates(candidates)

    def _faq_answer_candidates(
        self,
        message: str,
        *,
        active_task: dict[str, Any] | None,
        suspended_tasks: list[dict[str, Any]],
    ) -> list[RouteCandidate]:
        if self._faq_answer_gate is None:
            return []
        proposal = self._faq_answer_gate.propose(
            message,
            active_task=active_task,
            suspended_tasks=suspended_tasks,
        )
        if proposal is None:
            return []
        decision = proposal.to_route_decision()
        faq_answer = dict(decision.faq_answer or {})
        if active_task is not None and _is_ambiguous_active_faq_input(message):
            faq_answer["reasonCode"] = "AMBIGUOUS_ACTIVE_SOP"
            return [
                RouteCandidate(
                    candidate_id="clarify:faq_active_ambiguous",
                    candidate_type="CLARIFY",
                    target_id="FAQ_ACTIVE_AMBIGUOUS",
                    display_name="Clarify FAQ versus active SOP",
                    source="faq_exact",
                    score=max(0.0, min(1.0, float(proposal.confidence))),
                    score_breakdown=ScoreBreakdown(keyword=float(proposal.confidence), alias=0.0, semantic=0.0),
                    matched_terms=tuple(proposal.evidence.matched_terms),
                    risk_level="LOW",
                    requires_classifier=True,
                    reason="Active SOP input is ambiguous between FAQ answer and slot collection",
                    payload={"faq_answer": faq_answer},
                )
            ]
        faq_id = faq_answer.get("evidence", {}).get("faqId") if isinstance(faq_answer.get("evidence"), dict) else None
        return [
            RouteCandidate(
                candidate_id=f"faq:{faq_id or proposal.evidence.faq_id}",
                candidate_type="ANSWER_FAQ",
                target_id=f"faq:{faq_id or proposal.evidence.faq_id}",
                display_name=str(proposal.evidence.question or "FAQ answer"),
                source=str(faq_answer.get("sourceLayer") or "faq_exact"),
                score=max(0.0, min(1.0, float(proposal.confidence))),
                score_breakdown=ScoreBreakdown(keyword=float(proposal.confidence), alias=0.0, semantic=0.0),
                matched_terms=tuple(proposal.evidence.matched_terms),
                risk_level="LOW",
                requires_classifier=True,
                reason=str(decision.reason or "FAQ candidate recalled for central arbitration"),
                payload={"faq_answer": faq_answer},
            )
        ]

    def _faq_semantic_candidates(
        self,
        message: str,
        *,
        active_task: dict[str, Any] | None,
        suspended_tasks: list[dict[str, Any]],
    ) -> list[RouteCandidate]:
        decision = self._faq_semantic_decision(message, active_task, suspended_tasks)
        if decision is None:
            return []
        return _answer_decision_candidates(
            decision,
            candidate_prefix="faq_semantic",
            answer_key="faq_answer",
            answer_payload=decision.faq_answer or {},
        )

    def _rag_answer_candidates(
        self,
        message: str,
        *,
        active_task: dict[str, Any] | None,
        suspended_tasks: list[dict[str, Any]],
    ) -> list[RouteCandidate]:
        decision = self._rag_answer_decision(message, active_task, suspended_tasks)
        if decision is None:
            return []
        return _answer_decision_candidates(
            decision,
            candidate_prefix="rag",
            answer_key="rag_answer",
            answer_payload=decision.rag_answer or {},
        )

    def _agent_fallback_candidates(self, message: str, *, reason: str) -> list[RouteCandidate]:
        if self._fallback_agent is None:
            return []
        score = 0.72 if _looks_like_airport_facility_question(message) else 0.66
        return [
            RouteCandidate(
                candidate_id="agent:fallback",
                candidate_type="AGENT_FALLBACK",
                target_id="fallback_agent",
                display_name="Controlled fallback Agent",
                source="agent_candidate_recall",
                score=score,
                score_breakdown=ScoreBreakdown(keyword=0.0, alias=0.0, semantic=score),
                matched_terms=(),
                risk_level="MEDIUM",
                requires_classifier=True,
                reason=reason,
                payload={"deferred_agent": True},
            )
        ]

    def _faq_answer_decision(
        self,
        message: str,
        active_task: dict[str, Any] | None,
        suspended_tasks: list[dict[str, Any]],
    ) -> RouteDecision | None:
        if self._faq_answer_gate is None:
            return None
        proposal = self._faq_answer_gate.propose(
            message,
            active_task=active_task,
            suspended_tasks=suspended_tasks,
        )
        if proposal is None:
            return None
        if active_task is not None and _is_ambiguous_active_faq_input(message):
            faq_answer = dict(proposal.to_route_decision().faq_answer or {})
            faq_answer["reasonCode"] = "AMBIGUOUS_ACTIVE_SOP"
            return RouteDecision(
                action="CLARIFY",
                reason="Active SOP input is ambiguous between FAQ answer and slot collection",
                faq_answer=faq_answer,
            )
        return proposal.to_route_decision()

    def _faq_semantic_decision(
        self,
        message: str,
        active_task: dict[str, Any] | None,
        suspended_tasks: list[dict[str, Any]],
    ) -> RouteDecision | None:
        if self._faq_semantic_gate is None:
            return None
        return self._faq_semantic_gate.decide(
            message,
            active_task=active_task,
            suspended_tasks=suspended_tasks,
        )

    def _rag_answer_decision(
        self,
        message: str,
        active_task: dict[str, Any] | None,
        suspended_tasks: list[dict[str, Any]],
    ) -> RouteDecision | None:
        if self._rag_answer_gate is None:
            return None
        return self._rag_answer_gate.decide(
            message,
            active_task=active_task,
            suspended_tasks=suspended_tasks,
        )

    def _agent_fallback_decision(
        self,
        session_id: int,
        message: str,
        active_task: dict[str, Any] | None,
        suspended_tasks: list[dict[str, Any]],
    ) -> RouteDecision | None:
        if self._fallback_agent is None:
            return None
        output = self._fallback_agent.run(
            FallbackAgentRequest(
                message=message,
                active_task=active_task,
                suspended_tasks=suspended_tasks,
                recent_events=self._recent_events(session_id, limit=12),
            )
        )
        return self._agent_output_policy.decide(
            output,
            clarification_attempts=self._agent_clarification_attempts(session_id),
        )

    def _enabled_scope_fallback_candidates(self, enabled_sop_ids: frozenset[str]) -> list[RouteCandidate]:
        return self._finite_sop_fallback_candidates(
            enabled_sop_ids,
            source="enabled_scope_fallback",
            reason="Enabled SOP finite candidate fallback after explicit and semantic recall returned empty",
        )

    def _scoped_finite_fallback_candidates(
        self,
        message: str,
        enabled_sop_ids: frozenset[str] | None,
    ) -> list[RouteCandidate]:
        scope = enabled_sop_ids if enabled_sop_ids is not None else frozenset(self._manifests)
        candidates: list[RouteCandidate] = []
        for sop_id in sorted(scope):
            manifest = self._manifests[sop_id]
            matched_terms = _fallback_hint_terms(sop_id, message)
            if not matched_terms:
                continue
            score = min(0.68, 0.48 + len(matched_terms) * 0.04)
            candidates.append(
                RouteCandidate(
                    candidate_id=f"sop:{sop_id}",
                    candidate_type="SOP_INTENT",
                    target_id=sop_id,
                    display_name=manifest.display_name,
                    source="scoped_finite_fallback",
                    score=score,
                    score_breakdown=ScoreBreakdown(keyword=0.0, alias=0.0, semantic=score),
                    matched_terms=matched_terms,
                    risk_level="MEDIUM",
                    requires_classifier=True,
                    reason="Scoped finite fallback after shallow recall returned empty",
                )
            )
        return self._select_top_candidates(candidates)

    def _finite_sop_fallback_candidates(
        self,
        sop_ids: frozenset[str],
        *,
        source: str,
        reason: str,
    ) -> list[RouteCandidate]:
        candidates: list[RouteCandidate] = []
        for sop_id in sorted(sop_ids):
            manifest = self._manifests[sop_id]
            candidates.append(
                RouteCandidate(
                    candidate_id=f"sop:{sop_id}",
                    candidate_type="SOP_INTENT",
                    target_id=sop_id,
                    display_name=manifest.display_name,
                    source=source,
                    score=0.45,
                    score_breakdown=ScoreBreakdown(keyword=0.0, alias=0.0, semantic=0.45),
                    matched_terms=(),
                    risk_level="MEDIUM",
                    requires_classifier=True,
                    reason=reason,
                )
            )
        return candidates

    def _normalize_enabled_sop_ids(self, enabled_sop_ids: Sequence[str] | None) -> frozenset[str] | None:
        if enabled_sop_ids is None:
            return None
        return frozenset(sop_id for sop_id in enabled_sop_ids if sop_id in self._manifests)

    def _start_task(self, session_id: int, sop_id: str, result: SopExecutionResult) -> dict[str, Any]:
        task = self._repository.create_task(
            session_id,
            sop_id=sop_id,
            current_step=result.current_step,
            business_refs=result.collected,
        )
        checkpoint = self._repository.create_checkpoint(
            session_id,
            int(task["id"]),
            sop_id=sop_id,
            current_step=result.current_step,
            pending_prompt=result.pending_prompt,
            collected=result.collected,
            scoped_variables=result.checkpoint.scoped_variables,
            status=_checkpoint_status(result),
        )
        return self._repository.update_task_state(
            int(task["id"]),
            status="RUNNING",
            current_step=result.current_step,
            checkpoint_id=int(checkpoint["id"]),
            business_refs=result.collected,
        )

    def _suspend_task(self, session_id: int, task: dict[str, Any]) -> dict[str, Any]:
        checkpoint_row = self._repository.get_latest_checkpoint(int(task["id"]))
        adapter_checkpoint = self._adapter.suspend_sop(
            self._adapter_request(
                session_id,
                str(task["sop_id"]),
                task=task,
                checkpoint_row=checkpoint_row,
                collected=dict(task.get("business_refs") or {}),
            )
        )
        checkpoint = self._repository.create_checkpoint(
            session_id,
            int(task["id"]),
            sop_id=str(task["sop_id"]),
            current_step=adapter_checkpoint.current_step,
            pending_prompt=adapter_checkpoint.pending_prompt,
            collected=adapter_checkpoint.collected,
            scoped_variables=adapter_checkpoint.scoped_variables,
        )
        summary = f"{task['sop_id']} paused at {task['current_step']}"
        return self._repository.update_task_state(
            int(task["id"]),
            status="SUSPENDED",
            checkpoint_id=int(checkpoint["id"]),
            resume_summary=summary,
            business_refs=adapter_checkpoint.collected,
        )

    def _continue_active_task(
        self,
        session_id: int,
        active_task: dict[str, Any],
        message: str,
        decision: RouteDecision,
    ) -> RuntimeLabTurn:
        checkpoint = self._repository.get_latest_checkpoint(int(active_task["id"]))
        result = self._adapter.continue_sop(
            self._adapter_request(
                session_id,
                str(active_task["sop_id"]),
                message=message,
                task=active_task,
                checkpoint_row=checkpoint,
                collected=self._session_business_context(session_id),
            )
        )
        if result.status == SopExecutionStatus.FAILED:
            return self._adapter_failure_turn(session_id, result, decision)
        saved_checkpoint = self._repository.create_checkpoint(
            session_id,
            int(active_task["id"]),
            sop_id=str(active_task["sop_id"]),
            current_step=result.current_step,
            pending_prompt=result.pending_prompt,
            collected=result.collected,
            scoped_variables=result.checkpoint.scoped_variables,
            status=_checkpoint_status(result),
        )
        if result.status == SopExecutionStatus.COMPLETED:
            completed = self._repository.update_task_state(
                int(active_task["id"]),
                status="COMPLETED",
                current_step=result.current_step,
                checkpoint_id=int(saved_checkpoint["id"]),
                business_refs=result.collected,
            )
            complete_decision = RouteDecision(
                action="COMPLETE_TASK",
                reason="Active SOP completed after confirmation",
                active_task_id=int(completed["id"]),
            )
            self._repository.append_event(
                session_id,
                "TASK_COMPLETED",
                {"taskId": completed["id"], "sopId": completed["sop_id"]},
            )
            resume_offer = self._build_resume_offer(session_id)
            if resume_offer is not None:
                self._repository.append_event(session_id, "RESUME_OFFERED", resume_offer)
            return self._turn(session_id, result.reply, complete_decision, resume_offer=resume_offer)

        task = self._repository.update_task_state(
            int(active_task["id"]),
            status="RUNNING",
            current_step=result.current_step,
            checkpoint_id=int(saved_checkpoint["id"]),
            business_refs=result.collected,
        )
        self._repository.append_event(
            session_id,
            "TASK_CONTINUED",
            {"taskId": task["id"], "sopId": task["sop_id"], "currentStep": task["current_step"]},
        )
        return self._turn(session_id, result.reply, decision)

    def _resume_task(self, session_id: int, decision: RouteDecision, message: str) -> RuntimeLabTurn:
        suspended_tasks = self._repository.list_tasks(session_id, statuses={"SUSPENDED"})
        if not suspended_tasks:
            return self._turn(session_id, "没有可恢复的暂停流程。", RouteDecision(action="NO_MATCH", reason="No suspended task"))
        task = suspended_tasks[0]
        checkpoint = self._repository.get_latest_checkpoint(int(task["id"]))
        result = self._adapter.resume_sop(
            self._adapter_request(
                session_id,
                str(task["sop_id"]),
                message=message,
                task=task,
                checkpoint_row=checkpoint,
                collected=self._session_business_context(session_id),
            )
        )
        if result.status == SopExecutionStatus.FAILED:
            return self._adapter_failure_turn(session_id, result, decision)
        saved_checkpoint = self._repository.create_checkpoint(
            session_id,
            int(task["id"]),
            sop_id=str(task["sop_id"]),
            current_step=result.current_step or (str(checkpoint["current_step"]) if checkpoint else str(task["current_step"])),
            pending_prompt=result.pending_prompt,
            collected=result.collected,
            scoped_variables=result.checkpoint.scoped_variables,
            status=_checkpoint_status(result),
        )
        current_step = str(saved_checkpoint["current_step"])
        resumed = self._repository.update_task_state(
            int(task["id"]),
            status="RUNNING",
            current_step=current_step,
            checkpoint_id=int(saved_checkpoint["id"]),
            business_refs=result.collected,
        )
        self._repository.append_event(
            session_id,
            "TASK_RESUMED",
            {"taskId": resumed["id"], "sopId": resumed["sop_id"], "currentStep": resumed["current_step"]},
        )
        return self._turn(session_id, result.reply or "已恢复刚才的流程。请继续提供信息。", decision)

    def _build_resume_offer(self, session_id: int) -> dict[str, Any] | None:
        suspended_tasks = self._repository.list_tasks(session_id, statuses={"SUSPENDED"})
        if not suspended_tasks:
            return None
        task = suspended_tasks[0]
        return {
            "taskId": task["id"],
            "sopId": task["sop_id"],
            "resumeSummary": task["resume_summary"],
            "prompt": "是否继续刚才中断的流程？",
        }

    def _session_business_context(self, session_id: int) -> dict[str, Any]:
        context: dict[str, Any] = {}
        for task in self._repository.list_tasks(session_id):
            task_refs = task.get("business_refs")
            if isinstance(task_refs, dict):
                context.update(task_refs)
            checkpoint = self._repository.get_latest_checkpoint(int(task["id"]))
            if checkpoint is None:
                continue
            collected = checkpoint.get("collected")
            if isinstance(collected, dict):
                context.update(collected)
        return context

    def _recent_events(self, session_id: int, *, limit: int) -> list[dict[str, Any]]:
        events = self._repository.list_events(session_id)
        return events[-limit:]

    def _recent_completed_confirmation_decision(
        self,
        session_id: int,
        message: str,
        active_task: dict[str, Any] | None,
        suspended_tasks: list[dict[str, Any]],
    ) -> RouteDecision | None:
        if active_task is not None or suspended_tasks:
            return None
        text = message.strip()
        if not _looks_like_duplicate_confirmation(text):
            return None
        completed_tasks = self._repository.list_tasks(session_id, statuses={"COMPLETED"})
        if not completed_tasks:
            return None
        task = completed_tasks[-1]
        sop_id = str(task.get("sop_id") or "")
        manifest = self._manifests.get(sop_id)
        if manifest is None or not _message_confirms_completed_sop(text, manifest.display_name, sop_id):
            return None
        return RouteDecision(
            action="AGENT_FALLBACK",
            reason="Recent completed SOP duplicate confirmation ignored",
            agent_answer={
                "sourceLayer": "state_policy",
                "reasonCode": "RECENT_TASK_ALREADY_COMPLETED",
                "responseType": "answer",
                "answer": f"刚才的{manifest.display_name}流程已完成，无需重复确认。",
                "clarificationQuestion": "",
                "handoffReason": "",
                "confidence": 1.0,
                "citations": [],
                "safetyFlags": [],
                "proposedActions": [],
                "mutatesSopState": False,
                "policyEvidence": {"accepted": True, "taskId": task.get("id"), "sopId": sop_id},
            },
        )

    def _agent_clarification_attempts(self, session_id: int) -> int:
        return sum(1 for event in self._repository.list_events(session_id) if event["event_type"] == "AGENT_CLARIFICATION_ASKED")

    def _turn(
        self,
        session_id: int,
        reply: str,
        decision: RouteDecision,
        resume_offer: dict[str, Any] | None = None,
    ) -> RuntimeLabTurn:
        return RuntimeLabTurn(
            reply=reply,
            route_decision=decision,
            active_task=self._repository.get_active_task(session_id),
            suspended_tasks=self._repository.list_tasks(session_id, statuses={"SUSPENDED"}),
            resume_offer=resume_offer,
            events=self._repository.list_events(session_id),
        )

    def _handoff_turn(self, session_id: int, message: str, decision: RouteDecision) -> RuntimeLabTurn:
        self._repository.append_event(session_id, "HANDOFF_DECIDED", _decision_payload(decision))
        snapshot = self._handoff_context_snapshot(session_id, message, decision)
        ticket_id: int | None = None
        if self._handoff_service is not None:
            ticket = self._handoff_service.create_ticket(
                {
                    "session_id": str(session_id),
                    "conversation_id": f"runtime-lab:{session_id}",
                    "user_id": "",
                    "channel": "runtime_lab",
                    "queue": "general",
                    "reason": snapshot["reasonCode"],
                    "priority": "high",
                    "sla_minutes": 30,
                    "transcript_snapshot": snapshot["recentTranscript"],
                    "context_snapshot": snapshot,
                }
            )
            raw_ticket_id = ticket.get("id")
            ticket_id = int(raw_ticket_id) if raw_ticket_id is not None else None
        self._repository.append_event(
            session_id,
            "HANDOFF_REQUESTED",
            {"ticketId": ticket_id, "contextSnapshot": snapshot},
        )
        return self._turn(session_id, "已为您转接人工客服，请稍候。", decision)

    def _faq_turn(self, session_id: int, decision: RouteDecision) -> RuntimeLabTurn:
        faq_answer = decision.faq_answer or {}
        self._repository.append_event(session_id, "FAQ_ANSWERED", faq_answer)
        return self._turn(session_id, str(faq_answer.get("answer") or ""), decision)

    def _rag_turn(self, session_id: int, decision: RouteDecision) -> RuntimeLabTurn:
        rag_answer = decision.rag_answer or {}
        self._repository.append_event(session_id, "RAG_ANSWERED", rag_answer)
        return self._turn(session_id, str(rag_answer.get("answer") or ""), decision)

    def _agent_fallback_turn(
        self,
        session_id: int,
        message: str,
        active_task: dict[str, Any] | None,
        suspended_tasks: list[dict[str, Any]],
        decision: RouteDecision,
    ) -> RuntimeLabTurn:
        if not decision.agent_answer:
            agent_decision = self._agent_fallback_decision(session_id, message, active_task, suspended_tasks)
            if agent_decision is None:
                return self._turn(session_id, "请补充更多信息，我再继续为您处理。", RouteDecision(action="CLARIFY", reason=decision.reason))
            agent_decision = _copy_route_evidence(agent_decision, decision)
            self._repository.append_event(session_id, "AGENT_POLICY_DECISION", _decision_payload(agent_decision))
            if agent_decision.action == "HANDOFF_TO_HUMAN":
                return self._handoff_turn(session_id, message, agent_decision)
            if agent_decision.action == "CLARIFY":
                return self._agent_clarify_turn(session_id, agent_decision)
            decision = agent_decision
        agent_answer = decision.agent_answer or {}
        self._repository.append_event(session_id, "AGENT_FALLBACK_ANSWERED", agent_answer)
        return self._turn(session_id, str(agent_answer.get("answer") or ""), decision)

    def _agent_clarify_turn(self, session_id: int, decision: RouteDecision) -> RuntimeLabTurn:
        agent_answer = decision.agent_answer or {}
        reason_code = str(agent_answer.get("reasonCode") or "")
        event_type = "AGENT_CLARIFICATION_ASKED" if reason_code == "AGENT_CLARIFICATION" else "AGENT_OUTPUT_REJECTED"
        self._repository.append_event(session_id, event_type, agent_answer)
        reply = str(
            agent_answer.get("clarificationQuestion")
            or agent_answer.get("answer")
            or "请补充更多信息，我再继续为您处理。"
        )
        return self._turn(session_id, reply, decision)

    def _handoff_context_snapshot(
        self,
        session_id: int,
        message: str,
        decision: RouteDecision,
    ) -> dict[str, Any]:
        handoff = decision.handoff or {}
        active_task = self._repository.get_active_task(session_id)
        suspended_tasks = self._repository.list_tasks(session_id, statuses={"SUSPENDED"})
        return {
            "sourceLayer": handoff.get("sourceLayer") or "system_policy",
            "reasonCode": handoff.get("reasonCode") or "UNSPECIFIED",
            "userMessage": message,
            "activeTaskSummary": _task_summary(active_task),
            "suspendedTaskSummaries": [_task_summary(task) for task in suspended_tasks],
            "routeEvidence": _decision_payload(decision),
            "recentTranscript": self._session_user_history(session_id),
            "businessRefs": self._session_business_context(session_id),
        }

    def _adapter_request(
        self,
        session_id: int,
        sop_id: str,
        message: str = "",
        task: dict[str, Any] | None = None,
        checkpoint_row: dict[str, Any] | None = None,
        collected: dict[str, Any] | None = None,
    ) -> SopExecutionRequest:
        checkpoint = _sop_checkpoint_from_row(task, checkpoint_row)
        inherited_context = dict(collected or {})
        sop_context = _context_for_sop(sop_id, inherited_context)
        context_reference = _references_session_context(message)
        business_context_reference = context_reference and not _is_resume_only_reference(message)
        saved = sop_context if business_context_reference else {}
        if checkpoint is not None:
            saved = dict(sop_context) if business_context_reference else {}
            saved.update(dict(checkpoint.collected))
            checkpoint = _checkpoint_with_collected(checkpoint, saved)
        metadata: dict[str, Any] = {
            "runtime": "runtime_lab",
            "contextReference": business_context_reference,
        }
        if sop_context:
            metadata["inheritedContext"] = sop_context
        history = self._session_user_history(session_id, current_message=message)
        if history and business_context_reference:
            metadata["history"] = history
        return SopExecutionRequest(
            runtime_session_id=session_id,
            runtime_task_id=int(task["id"]) if task is not None else None,
            sop_id=sop_id,
            message=message,
            checkpoint=checkpoint,
            collected=saved,
            business_refs=dict(task.get("business_refs") or {}) if task is not None else {},
            metadata=metadata,
        )

    def _session_user_history(
        self,
        session_id: int,
        *,
        current_message: str = "",
        limit: int = 10,
    ) -> list[dict[str, str]]:
        history: list[dict[str, str]] = []
        for event in self._repository.list_events(session_id):
            if str(event.get("event_type") or "") != "USER_MESSAGE":
                continue
            payload = event.get("payload")
            if not isinstance(payload, dict):
                continue
            content = str(payload.get("message") or "").strip()
            if content:
                history.append({"role": "user", "content": content})
        if current_message and history and history[-1]["content"] == current_message:
            history = history[:-1]
        return history[-limit:]

    def _adapter_failure_turn(
        self,
        session_id: int,
        result: SopExecutionResult,
        decision: RouteDecision,
    ) -> RuntimeLabTurn:
        self._repository.append_event(
            session_id,
            "ERROR",
            {
                "source": "SOP_ADAPTER",
                "error": result.error or {"code": "SOP_FAILED", "message": "SOP execution failed"},
                "events": result.events,
            },
        )
        return self._turn(session_id, "SOP执行失败，请稍后重试或转人工。", decision)

    def _ensure_session_exists(self, session_id: int) -> None:
        if self._repository.get_session(session_id) is None:
            raise BizError(ErrorCode.NOT_FOUND, "Runtime lab session not found")


def _decision_payload(decision: RouteDecision) -> dict[str, Any]:
    return {
        "action": decision.action,
        "reason": decision.reason,
        "targetSopId": decision.target_sop_id,
        "activeTaskId": decision.active_task_id,
        "matchedKeyword": decision.matched_keyword,
        "candidates": decision.candidates or [],
        "candidateSources": decision.candidate_sources or [],
        "policyGate": decision.policy_gate,
        "classifierRequest": decision.classifier_request,
        "classifierResult": decision.classifier_result,
        "finalDecision": decision.final_decision or _final_decision_payload(decision),
        "handoff": decision.handoff,
        "faqAnswer": decision.faq_answer,
        "ragAnswer": decision.rag_answer,
        "agentAnswer": decision.agent_answer,
    }


def _copy_route_evidence(decision: RouteDecision, evidence_source: RouteDecision) -> RouteDecision:
    return RouteDecision(
        action=decision.action,
        reason=decision.reason,
        target_sop_id=decision.target_sop_id,
        active_task_id=decision.active_task_id,
        matched_keyword=decision.matched_keyword,
        candidates=evidence_source.candidates,
        candidate_sources=evidence_source.candidate_sources,
        policy_gate=evidence_source.policy_gate,
        classifier_request=evidence_source.classifier_request,
        classifier_result=evidence_source.classifier_result,
        final_decision=decision.final_decision,
        handoff=decision.handoff,
        faq_answer=decision.faq_answer,
        rag_answer=decision.rag_answer,
        agent_answer=decision.agent_answer,
    )


def _answer_decision_candidates(
    decision: RouteDecision,
    *,
    candidate_prefix: str,
    answer_key: str,
    answer_payload: dict[str, Any],
) -> list[RouteCandidate]:
    if not answer_payload:
        return []
    confidence = max(0.0, min(1.0, float(answer_payload.get("confidence") or 0.0)))
    source_layer = str(answer_payload.get("sourceLayer") or candidate_prefix)
    reason_code = str(answer_payload.get("reasonCode") or decision.action)
    evidence = answer_payload.get("evidence") if isinstance(answer_payload.get("evidence"), dict) else {}
    retrieval = answer_payload.get("retrievalEvidence") if isinstance(answer_payload.get("retrievalEvidence"), dict) else {}
    target_suffix = _answer_candidate_target_suffix(evidence, retrieval, reason_code)
    matched_terms = tuple(str(term) for term in evidence.get("matchedTerms") or ())
    candidate_type = decision.action if decision.action in {"ANSWER_FAQ", "ANSWER_RAG"} else "CLARIFY"
    payload = {answer_key: dict(answer_payload)}
    return [
        RouteCandidate(
            candidate_id=f"{candidate_prefix}:{target_suffix}",
            candidate_type=candidate_type,
            target_id=f"{candidate_prefix}:{target_suffix}",
            display_name=_answer_candidate_display_name(answer_payload, evidence, retrieval, reason_code),
            source=source_layer,
            score=confidence,
            score_breakdown=ScoreBreakdown(keyword=0.0, alias=0.0, semantic=confidence),
            matched_terms=matched_terms,
            risk_level="LOW" if candidate_type != "CLARIFY" else "MEDIUM",
            requires_classifier=True,
            reason=str(decision.reason or f"{source_layer} candidate recalled for central arbitration"),
            payload=payload,
        )
    ]


def _answer_candidate_target_suffix(
    evidence: dict[str, Any],
    retrieval: dict[str, Any],
    reason_code: str,
) -> str:
    faq_id = evidence.get("faqId")
    if faq_id is not None:
        return f"faq:{faq_id}"
    top_chunks = retrieval.get("topChunks") if isinstance(retrieval.get("topChunks"), list) else []
    if top_chunks and isinstance(top_chunks[0], dict) and top_chunks[0].get("sourceId"):
        return str(top_chunks[0]["sourceId"]).replace(":", "_")
    return reason_code


def _answer_candidate_display_name(
    answer_payload: dict[str, Any],
    evidence: dict[str, Any],
    retrieval: dict[str, Any],
    reason_code: str,
) -> str:
    question = evidence.get("question")
    if question:
        return str(question)
    top_chunks = retrieval.get("topChunks") if isinstance(retrieval.get("topChunks"), list) else []
    if top_chunks and isinstance(top_chunks[0], dict) and top_chunks[0].get("title"):
        return str(top_chunks[0]["title"])
    answer = str(answer_payload.get("answer") or "").strip()
    return answer[:48] if answer else reason_code


def _task_summary(task: dict[str, Any] | None) -> dict[str, Any] | None:
    if task is None:
        return None
    return {
        "taskId": task["id"],
        "sopId": task["sop_id"],
        "status": task["status"],
        "currentStep": task["current_step"],
        "resumeSummary": task["resume_summary"],
        "businessRefs": task.get("business_refs") or {},
    }


def _final_decision_payload(decision: RouteDecision) -> dict[str, Any]:
    payload = {
        "action": decision.action,
        "targetSopId": decision.target_sop_id,
        "activeTaskId": decision.active_task_id,
    }
    if decision.action in _SOP_ARBITRATION_ACTIONS:
        payload["sourceLayer"] = "sop_arbitration"
        payload["reasonCode"] = decision.action
    if decision.handoff:
        payload["sourceLayer"] = decision.handoff.get("sourceLayer")
        payload["reasonCode"] = decision.handoff.get("reasonCode")
    if decision.faq_answer:
        payload["sourceLayer"] = decision.faq_answer.get("sourceLayer")
        payload["reasonCode"] = decision.faq_answer.get("reasonCode")
    if decision.rag_answer:
        payload["sourceLayer"] = decision.rag_answer.get("sourceLayer")
        payload["reasonCode"] = decision.rag_answer.get("reasonCode")
    if decision.agent_answer:
        payload["sourceLayer"] = decision.agent_answer.get("sourceLayer")
        payload["reasonCode"] = decision.agent_answer.get("reasonCode")
    return payload


def _is_low_confidence_rag(decision: RouteDecision) -> bool:
    return (
        decision.action == "CLARIFY"
        and (decision.rag_answer or {}).get("reasonCode") == "RAG_LOW_CONFIDENCE"
    )


def _is_answer_rag(decision: RouteDecision) -> bool:
    return (
        decision.action == "ANSWER_RAG"
        and (decision.rag_answer or {}).get("reasonCode") == "RAG_HIGH_CONFIDENCE"
    )


_SOP_ARBITRATION_ACTIONS = {
    "CONTINUE_ACTIVE_SOP",
    "START_SOP",
    "SUSPEND_AND_START",
    "RESUME_TASK",
    "REJECT_SWITCH_CONTINUE_ACTIVE",
    "REJECT_SWITCH_SUSPENDED_LIMIT",
    "COMPLETE_TASK",
}


def _classifier_failure_result(exc: Exception, classifier: Any, classifier_input: ClassifierInput) -> ClassifierResult:
    class_name = classifier.__class__.__name__
    mode = "llm_error" if "Llm" in class_name or "LLM" in class_name else "classifier_error"
    if mode == "llm_error":
        try:
            fallback = FakeConstrainedIntentClassifier().classify(classifier_input)
        except Exception:
            fallback = None
        if fallback is not None and fallback.selected_action != "CLARIFY":
            return ClassifierResult(
                selected_action=fallback.selected_action,
                selected_candidate_id=fallback.selected_candidate_id,
                confidence=fallback.confidence,
                rationale=f"LLM classifier failed; deterministic finite-candidate fallback selected ({exc.__class__.__name__})",
                needs_clarification=False,
                clarification_question=None,
                arbitrator_mode="llm_error_fallback",
                used_real_llm=False,
                debug={"error": exc.__class__.__name__},
            )
    return ClassifierResult(
        selected_action="CLARIFY",
        selected_candidate_id=None,
        confidence=0.0,
        rationale=f"Classifier failed; fallback to clarification ({exc.__class__.__name__})",
        needs_clarification=True,
        clarification_question=(
            "请问您想办理订票、票价、团队票、增值服务、退票、改签、资料修改、发票、行李、"
            "值机、航班动态、特殊协助、宠物乘机、异常航班还是会员里程？"
        ),
        arbitrator_mode=mode,
        used_real_llm=False,
    )


def _route_step(name: str, started_at: float, input_payload: Any, output_payload: Any) -> dict[str, Any]:
    return {
        "id": name,
        "name": name,
        "label": _route_step_label(name),
        "elapsedMs": _elapsed_ms(started_at),
        "input": input_payload,
        "output": output_payload,
        "usage": {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0, "estimated": False},
    }


def _route_step_label(name: str) -> str:
    return {
        "candidate_recall": "候选召回",
        "enabled_scope_fallback": "接入范围候选兜底",
        "finite_intent_fallback": "有限意图全集兜底",
        "scoped_finite_fallback": "有限意图局部兜底",
        "no_signal_clarify": "无业务信号澄清",
        "faq_exact": "FAQ精确回答",
        "faq_semantic": "FAQ语义回答",
        "rag_policy": "RAG知识兜底",
        "agent_policy": "受控Agent兜底",
        "recent_completed_guard": "重复确认保护",
        "pre_classifier_policy": "轻量策略闸门",
        "llm_intent_arbitration": "LLM有限意图仲裁",
        "post_classifier_policy": "仲裁后策略闸门",
    }.get(name, name)


def _elapsed_ms(started_at: float) -> int:
    return int((perf_counter() - started_at) * 1000)


def _references_session_context(message: str) -> bool:
    normalized = message.strip().lower()
    reset_terms = (
        "另一个",
        "另外一个",
        "别人",
        "其他人",
        "新乘机人",
        "换个人",
        "不是刚才",
        "不是之前",
        "给同事",
        "给朋友",
        "给家人",
        "我同事",
        "我朋友",
    )
    if any(term in normalized for term in reset_terms):
        return False
    reference_terms = (
        "刚才",
        "刚刚",
        "之前",
        "上一个",
        "上一单",
        "那张",
        "这张",
        "这个订单",
        "那个订单",
        "同一个",
        "同一趟",
        "同航班",
        "这趟",
        "这次",
        "这次行程",
        "本次行程",
        "一起走",
        "一样",
        "照旧",
        "继续刚才",
        "刚订",
        "刚出票",
        "原订单",
    )
    return any(term in normalized for term in reference_terms)


def _is_resume_only_reference(message: str) -> bool:
    normalized = message.strip().lower()
    if "继续" not in normalized and "resume" not in normalized:
        return False
    explicit_business_reference_terms = (
        "那张",
        "这张",
        "这个订单",
        "那个订单",
        "订单",
        "同一个",
        "同一趟",
        "同航班",
        "这趟",
        "这次",
        "本次行程",
        "一起走",
        "一样",
        "照旧",
        "刚订",
        "刚出票",
        "原订单",
    )
    return not any(term in normalized for term in explicit_business_reference_terms)


def _is_ambiguous_active_faq_input(message: str) -> bool:
    text = message.strip()
    if not _looks_like_question(text):
        return False
    return _looks_like_slot_payload(text)


def _looks_like_question(text: str) -> bool:
    return any(term in text for term in ("?", "？", "吗", "怎么", "如何", "能不能", "可以"))


def _looks_like_slot_payload(text: str) -> bool:
    if any(term in text for term in ("订单", "手机号", "证件", "票号")):
        return True
    return bool(re.search(r"[A-Za-z]{1,6}-?\d{2,}|\d{6,}", text))


FALLBACK_HINTS: dict[str, tuple[str, ...]] = {
    "flight_booking": ("订", "定", "买", "购", "预订", "预定", "出票", "可售"),
    "fare_quote": ("票价", "价格", "多少钱", "报价", "便宜", "贵"),
    "group_booking": ("团队", "团体", "多人", "公司", "集体", "团建"),
    "ancillary_sales": ("加购", "贵宾厅", "保险", "餐食", "接送机", "升舱券", "附加"),
    "refund_ticket": ("退票", "退款", "退费", "取消", "不飞", "退"),
    "change_flight": ("改签", "改航班", "换航班", "改日期", "改时间", "调整", "改", "换"),
    "passenger_info_change": ("证件", "姓名", "联系人", "资料", "乘机人信息", "信息错", "填错", "更正"),
    "invoice_apply": ("发票", "报销", "凭证", "开票"),
    "baggage_service": ("行李", "托运", "超重", "随身", "运动器材"),
    "seat_checkin": ("座位", "值机", "登机牌", "靠窗", "过道"),
    "flight_status": ("航班动态", "航班状态", "延误", "登机口", "起飞", "到达", "接人", "动态"),
    "special_assistance": ("轮椅", "协助", "老人", "孕妇", "无障碍", "行动不便"),
    "pet_cabin": ("宠物", "猫", "狗", "航空箱", "疫苗"),
    "irregular_flight": ("异常航班", "不正常", "备降", "签转", "非自愿", "延误四小时", "航班取消"),
    "membership_service": ("里程", "积分", "会员", "常旅客", "补登"),
}


SOP_CONTEXT_KEYS: dict[str, frozenset[str]] = {
    "flight_booking": frozenset({"route", "travel_time", "passenger_name", "phone"}),
    "fare_quote": frozenset({"route", "travel_time"}),
    "group_booking": frozenset({"route", "travel_time", "passenger_count"}),
    "ancillary_sales": frozenset({"order_no", "phone", "passenger_name", "service_items"}),
    "refund_ticket": frozenset({"order_no", "phone", "passenger_name"}),
    "change_flight": frozenset({"order_no", "phone", "passenger_name", "target_time"}),
    "passenger_info_change": frozenset({"order_no", "phone", "passenger_name", "change_detail"}),
    "invoice_apply": frozenset({"order_no", "phone", "passenger_name", "invoice_title"}),
    "baggage_service": frozenset({"order_no", "phone", "passenger_name", "baggage_need"}),
    "seat_checkin": frozenset({"order_no", "phone", "passenger_name", "seat_preference"}),
    "flight_status": frozenset({"flight_no"}),
    "special_assistance": frozenset({"order_no", "phone", "passenger_name", "assistance_need"}),
    "pet_cabin": frozenset({"order_no", "phone", "passenger_name", "pet_info"}),
    "irregular_flight": frozenset({"order_no", "phone", "passenger_name", "issue_detail"}),
    "membership_service": frozenset({"order_no", "phone", "passenger_name", "member_no"}),
}


def _context_for_sop(sop_id: str, context: dict[str, Any]) -> dict[str, Any]:
    allowed = SOP_CONTEXT_KEYS.get(sop_id)
    if not allowed:
        return dict(context)
    return {key: value for key, value in context.items() if key in allowed}


def _fallback_hint_terms(sop_id: str, message: str) -> tuple[str, ...]:
    text = message.strip()
    if not text:
        return ()
    if _looks_like_airport_facility_question(text):
        return ()
    terms = [term for term in FALLBACK_HINTS.get(sop_id, ()) if term in text]
    if sop_id == "flight_booking" and terms and not any(term in text for term in ("航班", "机票", "飞机票", "票")):
        return ()
    return tuple(dict.fromkeys(terms))


def _looks_like_airport_facility_question(text: str) -> bool:
    facility_terms = ("机场", "候机楼", "柜台", "停车", "酒店", "打印店", "寄存", "WiFi", "wifi", "大巴", "贵宾楼")
    question_terms = ("吗", "么", "怎么", "哪里", "几点", "收费", "旁边", "附近", "有没有")
    return any(term in text for term in facility_terms) and any(term in text for term in question_terms)


def _looks_like_duplicate_confirmation(text: str) -> bool:
    return any(term in text for term in ("确认", "好的", "可以", "按这个")) and len(text) <= 24


def _message_confirms_completed_sop(text: str, display_name: str, sop_id: str) -> bool:
    terms_by_sop = {
        "flight_booking": ("出票", "预订", "订票", "机票"),
        "fare_quote": ("票价", "报价"),
        "group_booking": ("团队", "团体票"),
        "ancillary_sales": ("加购", "增值", "餐食", "保险", "贵宾厅"),
        "refund_ticket": ("退票", "退款"),
        "change_flight": ("改签", "改航班", "换航班"),
        "passenger_info_change": ("资料", "信息", "证件", "姓名"),
        "invoice_apply": ("发票", "开票"),
        "baggage_service": ("行李", "加购"),
        "seat_checkin": ("选座", "值机"),
        "flight_status": ("航班动态", "航班状态", "继续关注"),
        "special_assistance": ("特殊协助", "轮椅"),
        "pet_cabin": ("宠物", "托运"),
        "irregular_flight": ("异常航班", "签转"),
        "membership_service": ("会员", "里程"),
    }
    terms = (display_name, *terms_by_sop.get(sop_id, ()))
    return any(term and term in text for term in terms)


def _looks_like_sop_request(message: str) -> bool:
    request_markers = (
        "我要",
        "我想",
        "帮我",
        "办理",
        "申请",
        "订机票",
        "买票",
        "退票",
        "改签",
        "开发票",
        "值机",
        "托运",
    )
    return any(marker in message for marker in request_markers)


def _looks_like_strong_sop_request(message: str) -> bool:
    text = message.strip()
    if _explicitly_denies_sop_transaction(text):
        return False
    phrase_terms = (
        "帮我改签",
        "我要改签",
        "我想改签",
        "办理改签",
        "改签到",
        "改签到",
        "帮我退票",
        "我要退票",
        "我想退票",
        "办理退票",
        "帮我订",
        "我要订",
        "我想订",
        "我要买票",
        "帮我买票",
        "给这张票加购",
        "帮我加购",
        "我要加购",
        "我想加购",
        "我要开发票",
        "我想开发票",
        "帮我开发票",
        "帮我值机",
        "我要值机",
        "我要选座",
        "帮我选座",
        "办理宠物",
        "帮我办理宠物",
    )
    if any(term in text for term in phrase_terms):
        return True
    action_terms = ("帮我", "我要", "我想", "办理", "申请", "提交", "现在就")
    sop_terms = (
        "退票",
        "改签",
        "订票",
        "买票",
        "机票",
        "加购",
        "行李",
        "开发票",
        "开票",
        "值机",
        "选座",
        "宠物乘机",
        "宠物托运",
    )
    return any(term in text for term in action_terms) and any(term in text for term in sop_terms)


def _explicitly_denies_sop_transaction(message: str) -> bool:
    denial_terms = (
        "不是要办理",
        "不是办理",
        "不办理",
        "不是要办",
        "不办",
        "先不",
        "现在不",
    )
    consultation_terms = ("只是问", "只想问", "就想问", "想问", "咨询", "了解")
    return any(term in message for term in denial_terms) and any(term in message for term in consultation_terms)


def _should_agent_fallback_before_active_continue(
    candidates: Sequence[RouteCandidate],
    active_task: dict[str, Any] | None,
    message: str,
) -> bool:
    if active_task is None or len(candidates) != 1:
        return False
    candidate = candidates[0]
    if str(candidate.candidate_type) != "ACTIVE_TASK_CONTINUE" or candidate.score >= 0.6:
        return False
    return not _looks_like_active_sop_continuation_detail(message)


def _should_add_agent_fallback_candidate(
    candidates: Sequence[RouteCandidate],
    active_task: dict[str, Any] | None,
    message: str,
) -> bool:
    del active_task
    if not candidates:
        return False
    if _looks_like_airport_facility_question(message):
        return True
    has_sop_candidate = any(
        str(candidate.candidate_type) in {"SOP_INTENT", "ACTIVE_TASK_CONTINUE", "SUSPENDED_TASK_RESUME"}
        for candidate in candidates
    )
    has_low_confidence_answer_clarify = any(
        str(candidate.candidate_type) == "CLARIFY"
        and isinstance(candidate.payload, dict)
        and bool(candidate.payload.get("rag_answer") or candidate.payload.get("faq_answer"))
        for candidate in candidates
    )
    return has_low_confidence_answer_clarify and not has_sop_candidate


def _recover_clarify_result(
    result: ClassifierResult,
    candidates: Sequence[RouteCandidate],
    message: str,
    active_task: dict[str, Any] | None,
) -> ClassifierResult:
    if result.selected_action != "CLARIFY":
        return result
    if not result.used_real_llm:
        return result
    recovered = _clarify_answer_recovery_candidate(candidates)
    if recovered is None:
        recovered = _clarify_single_sop_recovery_candidate(candidates, message, active_task)
    if recovered is None:
        return result
    action = _action_for_recovered_candidate(recovered)
    debug = dict(result.debug or {})
    debug["clarifyRecovery"] = {
        "from": "CLARIFY",
        "candidateId": recovered.candidate_id,
        "candidateType": str(recovered.candidate_type),
        "targetId": recovered.target_id,
        "score": recovered.score,
    }
    return ClassifierResult(
        selected_action=action,
        selected_candidate_id=recovered.candidate_id,
        confidence=max(float(result.confidence or 0.0), recovered.score),
        rationale=f"{result.rationale}; recovered by finite-candidate policy guard",
        needs_clarification=False,
        clarification_question=None,
        arbitrator_mode=result.arbitrator_mode,
        used_real_llm=result.used_real_llm,
        debug=debug,
    )


def _clarify_answer_recovery_candidate(candidates: Sequence[RouteCandidate]) -> RouteCandidate | None:
    answer_candidates = [
        candidate
        for candidate in candidates
        if str(candidate.candidate_type) in {"ANSWER_FAQ", "ANSWER_RAG"} and candidate.score >= 0.86
    ]
    if not answer_candidates:
        return None
    return select_top_candidates(answer_candidates, top_k=1)[0]


def _clarify_single_sop_recovery_candidate(
    candidates: Sequence[RouteCandidate],
    message: str,
    active_task: dict[str, Any] | None,
) -> RouteCandidate | None:
    if active_task is not None:
        return None
    sop_candidates = [
        candidate
        for candidate in candidates
        if str(candidate.candidate_type) == "SOP_INTENT" and candidate.score >= 0.78
    ]
    target_ids = {candidate.target_id for candidate in sop_candidates}
    if len(target_ids) != 1:
        return None
    candidate = select_top_candidates(sop_candidates, top_k=1)[0]
    if not _can_recover_single_sop_clarify(message, candidate.target_id):
        return None
    return candidate


def _can_recover_single_sop_clarify(message: str, sop_id: str) -> bool:
    text = message.strip()
    if not text or _explicitly_denies_sop_transaction(text):
        return False
    if sop_id == "flight_status":
        return any(term in text for term in ("查航班", "航班现在", "到哪", "到哪了", "航班号", "接人", "等我"))
    return _looks_like_strong_sop_request(text)


def _action_for_recovered_candidate(candidate: RouteCandidate) -> str:
    candidate_type = str(candidate.candidate_type)
    if candidate_type == "ANSWER_FAQ":
        return "ANSWER_FAQ"
    if candidate_type == "ANSWER_RAG":
        return "ANSWER_RAG"
    if candidate_type == "SUSPENDED_TASK_RESUME":
        return "RESUME_TASK"
    if candidate_type == "AGENT_FALLBACK":
        return "AGENT_FALLBACK"
    if candidate_type == "SOP_INTENT":
        return "START_SOP"
    if candidate_type == "ACTIVE_TASK_CONTINUE":
        return "CONTINUE_ACTIVE_SOP"
    return "CLARIFY"


def _looks_like_active_sop_continuation_detail(message: str) -> bool:
    text = message.strip()
    if not text:
        return False
    if re.search(r"[A-Za-z]{2,}-?\d{2,}|\d{6,}|1[3-9]\d{9}", text):
        return True
    continuation_terms = (
        "订单",
        "票号",
        "手机号",
        "电话",
        "证件",
        "身份证",
        "护照",
        "乘机人",
        "确认",
        "好的",
        "可以",
        "是的",
        "继续",
        "取消",
    )
    return any(term in text for term in continuation_terms)


def _request_hash(
    message: str,
    enabled_sop_ids: Sequence[str] | None = None,
    policy_thresholds_override: Mapping[str, Any] | None = None,
    route_settings_signature: Mapping[str, Any] | None = None,
) -> str:
    scope = "<all>" if enabled_sop_ids is None else ",".join(sorted(set(enabled_sop_ids)))
    threshold_payload = _json_stable(policy_thresholds_override or {})
    route_settings_payload = _json_stable(route_settings_signature or {})
    return hashlib.sha256(f"{message}\0{scope}\0{threshold_payload}\0{route_settings_payload}".encode("utf-8")).hexdigest()


def _normalized_policy_thresholds_override(raw: Mapping[str, Any] | None) -> dict[str, Any]:
    if not raw:
        return {}
    allowed = {
        "strongAcceptThreshold",
        "classifierMinConfidence",
        "candidateTopK",
        "candidateSourceWeights",
        "llmArbitrationRequiredForNonHardStop",
        "faqKeywordMinScore",
        "faqKeywordMinMargin",
        "faqSemanticMinScore",
        "faqSemanticMinMargin",
        "ragMinScore",
        "ragLexicalAcceptThreshold",
    }
    normalized: dict[str, Any] = {}
    for key, value in raw.items():
        if key not in allowed:
            continue
        if key == "candidateSourceWeights":
            normalized[key] = value if isinstance(value, dict) else {}
        elif key == "llmArbitrationRequiredForNonHardStop":
            normalized[key] = bool(value)
        else:
            try:
                normalized[key] = float(value)
            except (TypeError, ValueError):
                continue
    return normalized


def _json_stable(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _checkpoint_status(result: SopExecutionResult) -> str:
    return "COMPLETED" if result.status == SopExecutionStatus.COMPLETED else "ACTIVE"


def _sop_checkpoint_from_row(
    task: dict[str, Any] | None,
    checkpoint: dict[str, Any] | None,
) -> SopCheckpoint | None:
    if checkpoint is None:
        return None
    collected = dict(checkpoint.get("collected") or {})
    scoped_variables = checkpoint.get("scoped_variables")
    task_id = int(task["id"]) if task is not None else int(checkpoint["task_id"])
    checkpoint_id = int(checkpoint["id"])
    current_step = str(checkpoint["current_step"])
    return SopCheckpoint(
        sop_runtime_id=f"runtime-lab:{task_id}:{checkpoint_id}",
        current_node_id=current_step,
        current_step=current_step,
        pending_prompt=str(checkpoint.get("pending_prompt") or ""),
        collected=collected,
        scoped_variables=dict(scoped_variables) if isinstance(scoped_variables, dict) else _scoped_variables(collected),
        version=1,
    )


def _checkpoint_with_collected(checkpoint: SopCheckpoint, collected: dict[str, Any]) -> SopCheckpoint:
    scoped_variables = dict(checkpoint.scoped_variables)
    for key, value in collected.items():
        scoped_variables.setdefault(f"conversation.{key}", value)
    return SopCheckpoint(
        sop_runtime_id=checkpoint.sop_runtime_id,
        current_node_id=checkpoint.current_node_id,
        current_step=checkpoint.current_step,
        pending_prompt=checkpoint.pending_prompt,
        collected=dict(collected),
        scoped_variables=scoped_variables,
        version=checkpoint.version,
    )


def _scoped_variables(collected: dict[str, Any]) -> dict[str, Any]:
    return {f"conversation.{key}": value for key, value in collected.items()}


def _with_evidence(
    decision: RouteDecision,
    candidates: Sequence[RouteCandidate],
    stage: str,
    classifier_input: ClassifierInput | None = None,
    classifier_result: ClassifierResult | None = None,
    route_steps: list[dict[str, Any]] | None = None,
    route_elapsed_ms: int | None = None,
) -> RouteDecision:
    candidate_payloads = [candidate.to_dict() for candidate in candidates]
    candidate_sources = sorted({str(candidate.source) for candidate in candidates})
    return RouteDecision(
        action=decision.action,
        reason=decision.reason,
        target_sop_id=decision.target_sop_id,
        active_task_id=decision.active_task_id,
        matched_keyword=decision.matched_keyword,
        candidates=candidate_payloads,
        candidate_sources=candidate_sources,
        policy_gate={
            "stage": stage,
            "decisionAction": decision.action,
            "steps": route_steps or [],
            "elapsedMs": route_elapsed_ms or 0,
        },
        classifier_request=classifier_input.to_llm_payload() if classifier_input else None,
        classifier_result=classifier_result.to_dict() if classifier_result else None,
        handoff=decision.handoff,
        faq_answer=decision.faq_answer,
        rag_answer=decision.rag_answer,
        agent_answer=decision.agent_answer,
        final_decision=_final_decision_payload(decision),
    )
