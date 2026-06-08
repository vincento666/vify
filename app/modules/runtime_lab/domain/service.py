import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Protocol

from app.core.errors import BizError, ErrorCode
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
    ) -> None:
        self._repository = repository
        self._manifests = mock_sop_manifests()
        self._adapter = adapter or FakeSopRuntimeAdapter()
        self._router = router or RuntimeLabRouter(self._adapter)
        self._explicit_signals = ExplicitSignalDetector(self._manifests)
        self._semantic_recall = MockSemanticCandidateRecall(self._manifests)
        self._classifier = classifier or FakeConstrainedIntentClassifier()
        self._policy_gate = PolicyGate(self._adapter)
        self._handoff_service = handoff_service
        self._faq_answer_gate = faq_answer_gate
        self._faq_semantic_gate = faq_semantic_gate
        self._rag_answer_gate = rag_answer_gate

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
        decision = self._semantic_decision(message, active_task, suspended_tasks, enabled_scope)
        self._repository.append_event(session_id, "ROUTE_DECISION", _decision_payload(decision))

        if decision.action == "HANDOFF_TO_HUMAN":
            return self._handoff_turn(session_id, message, decision)

        if decision.action == "ANSWER_FAQ":
            return self._faq_turn(session_id, decision)

        if decision.action == "ANSWER_RAG":
            return self._rag_turn(session_id, decision)

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
    ) -> RuntimeLabCommandResult:
        self._ensure_session_exists(session_id)
        request_hash = _request_hash(message, enabled_sop_ids)
        if idempotency_key:
            existing = self._repository.get_command_response(session_id, idempotency_key)
            if existing is not None:
                if existing["request_hash"] != request_hash:
                    raise BizError(ErrorCode.BAD_REQUEST, "Idempotency key reused with different request")
                return RuntimeLabCommandResult(dict(existing["response_payload"]), replayed=True)
        payload = format_turn(self.handle_message(session_id, message, enabled_sop_ids=enabled_sop_ids))
        if idempotency_key:
            self._repository.store_command_response(session_id, idempotency_key, request_hash, payload)
        return RuntimeLabCommandResult(payload, replayed=False)

    def list_tasks(self, session_id: int) -> list[dict[str, Any]]:
        return self._repository.list_tasks(session_id)

    def list_events(self, session_id: int) -> list[dict[str, Any]]:
        return self._repository.list_events(session_id)

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
        message: str,
        active_task: dict[str, Any] | None,
        suspended_tasks: list[dict[str, Any]],
        enabled_sop_ids: frozenset[str] | None,
    ) -> RouteDecision:
        route_started_at = perf_counter()
        route_steps: list[dict[str, Any]] = []
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
        faq_decision = self._faq_answer_decision(message, active_task, suspended_tasks)
        if faq_decision is not None:
            route_steps.append(
                _route_step(
                    "faq_exact",
                    perf_counter(),
                    {"message": message, "activeTask": active_task is not None},
                    {"decision": _decision_payload(faq_decision)},
                )
            )
            return _with_evidence(
                faq_decision,
                candidates,
                "faq_exact",
                route_steps=route_steps,
                route_elapsed_ms=_elapsed_ms(route_started_at),
            )
        semantic_faq_decision = self._faq_semantic_decision(message, active_task, suspended_tasks)
        if semantic_faq_decision is not None:
            route_steps.append(
                _route_step(
                    "faq_semantic",
                    perf_counter(),
                    {"message": message, "activeTask": active_task is not None},
                    {"decision": _decision_payload(semantic_faq_decision)},
                )
            )
            return _with_evidence(
                semantic_faq_decision,
                candidates,
                "faq_semantic",
                route_steps=route_steps,
                route_elapsed_ms=_elapsed_ms(route_started_at),
            )
        rag_decision = self._rag_answer_decision(message, active_task, suspended_tasks)
        if rag_decision is not None:
            route_steps.append(
                _route_step(
                    "rag_policy",
                    perf_counter(),
                    {"message": message, "activeTask": active_task is not None},
                    {"decision": _decision_payload(rag_decision)},
                )
            )
            if not (
                candidates
                and rag_decision.action == "CLARIFY"
                and (rag_decision.rag_answer or {}).get("reasonCode") == "RAG_LOW_CONFIDENCE"
                and _looks_like_sop_request(message)
            ):
                return _with_evidence(
                    rag_decision,
                    candidates,
                    "rag_policy",
                    route_steps=route_steps,
                    route_elapsed_ms=_elapsed_ms(route_started_at),
                )
        if not candidates:
            step_started_at = perf_counter()
            if enabled_sop_ids is not None and not enabled_sop_ids:
                return _with_evidence(
                    RouteDecision(action="NO_MATCH", reason="No enabled SOP candidate matched"),
                    (),
                    "enabled_scope",
                    route_steps=route_steps,
                    route_elapsed_ms=_elapsed_ms(route_started_at),
                )
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
            ),
            thresholds={"classifierMinConfidence": 0.6},
        )
        step_started_at = perf_counter()
        try:
            classifier_result = self._classifier.classify(classifier_input)
        except Exception as exc:
            classifier_result = _classifier_failure_result(exc, self._classifier)
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
        ]
        return select_top_candidates(candidates, top_k=5)

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
        return select_top_candidates(candidates, top_k=5)

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
        saved = sop_context if context_reference else {}
        if checkpoint is not None:
            saved = dict(sop_context) if context_reference else {}
            saved.update(dict(checkpoint.collected))
            checkpoint = _checkpoint_with_collected(checkpoint, saved)
        metadata: dict[str, Any] = {
            "runtime": "runtime_lab",
            "contextReference": context_reference,
        }
        if sop_context:
            metadata["inheritedContext"] = sop_context
        history = self._session_user_history(session_id, current_message=message)
        if history and (checkpoint is not None or context_reference):
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
    }


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
    if decision.handoff:
        payload["sourceLayer"] = decision.handoff.get("sourceLayer")
        payload["reasonCode"] = decision.handoff.get("reasonCode")
    if decision.faq_answer:
        payload["sourceLayer"] = decision.faq_answer.get("sourceLayer")
        payload["reasonCode"] = decision.faq_answer.get("reasonCode")
    if decision.rag_answer:
        payload["sourceLayer"] = decision.rag_answer.get("sourceLayer")
        payload["reasonCode"] = decision.rag_answer.get("reasonCode")
    return payload


def _classifier_failure_result(exc: Exception, classifier: Any) -> ClassifierResult:
    class_name = classifier.__class__.__name__
    mode = "llm_error" if "Llm" in class_name or "LLM" in class_name else "classifier_error"
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
        "一样",
        "照旧",
        "继续刚才",
        "刚订",
        "刚出票",
        "原订单",
    )
    return any(term in normalized for term in reference_terms)


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
    terms = [term for term in FALLBACK_HINTS.get(sop_id, ()) if term in text]
    if sop_id == "flight_booking" and terms and not any(term in text for term in ("航班", "机票", "飞机票", "票")):
        return ()
    return tuple(dict.fromkeys(terms))


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


def _request_hash(message: str, enabled_sop_ids: Sequence[str] | None = None) -> str:
    scope = "<all>" if enabled_sop_ids is None else ",".join(sorted(set(enabled_sop_ids)))
    return hashlib.sha256(f"{message}\0{scope}".encode("utf-8")).hexdigest()


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
        final_decision=_final_decision_payload(decision),
    )
