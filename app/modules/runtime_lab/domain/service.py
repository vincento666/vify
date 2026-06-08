import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from app.core.errors import BizError, ErrorCode
from app.modules.runtime_lab.domain.candidates import RouteCandidate, select_top_candidates
from app.modules.runtime_lab.domain.classifier import ClassifierInput, ClassifierResult, FakeConstrainedIntentClassifier
from app.modules.runtime_lab.domain.explicit_signals import ExplicitSignalDetector
from app.modules.runtime_lab.domain.payload import format_turn
from app.modules.runtime_lab.domain.policy import PolicyGate
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

        if decision.action == "START_SOP" and decision.target_sop_id is not None:
            result = self._adapter.start_sop(
                self._adapter_request(session_id, decision.target_sop_id, message=message)
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
                self._adapter_request(session_id, decision.target_sop_id, message=message)
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
            return self._resume_task(session_id, decision)

        if decision.action == "CLARIFY":
            return self._turn(session_id, "请问您想办理退票、改签、发票、行李、值机、航班动态、特殊协助、宠物乘机、异常航班还是会员里程？", decision)

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
        candidates = self._route_candidates(message, active_task, suspended_tasks, enabled_sop_ids)
        if not candidates:
            if enabled_sop_ids is not None:
                return _with_evidence(
                    RouteDecision(action="NO_MATCH", reason="No enabled SOP candidate matched"),
                    (),
                    "enabled_scope",
                )
            decision = self._router.decide(message, active_task=active_task, suspended_tasks=suspended_tasks)
            return _with_evidence(decision, (), "fallback")
        pre_decision = self._policy_gate.pre_classifier_decision(candidates, active_task, len(suspended_tasks))
        if pre_decision is not None:
            return _with_evidence(pre_decision, candidates, "pre_classifier")
        classifier_input = ClassifierInput(
            message=message,
            session_state={
                "activeTask": active_task is not None,
                "suspendedTaskCount": len(suspended_tasks),
                "enabledSopIds": sorted(enabled_sop_ids) if enabled_sop_ids is not None else None,
            },
            candidates=tuple(candidates),
            allowed_actions=(
                "HANDOFF_TO_HUMAN",
                "CONTINUE_ACTIVE_SOP",
                "START_SOP",
                "SUSPEND_AND_START",
                "RESUME_TASK",
                "CLARIFY",
                "REJECT_SWITCH_CONTINUE_ACTIVE",
            ),
            thresholds={"classifierMinConfidence": 0.6},
        )
        classifier_result = self._classifier.classify(classifier_input)
        decision = self._policy_gate.classifier_decision(classifier_result, candidates, active_task, len(suspended_tasks))
        return _with_evidence(decision, candidates, "post_classifier", classifier_input, classifier_result)

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
                collected=dict(active_task.get("business_refs") or {}),
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

    def _resume_task(self, session_id: int, decision: RouteDecision) -> RuntimeLabTurn:
        suspended_tasks = self._repository.list_tasks(session_id, statuses={"SUSPENDED"})
        if not suspended_tasks:
            return self._turn(session_id, "没有可恢复的暂停流程。", RouteDecision(action="NO_MATCH", reason="No suspended task"))
        task = suspended_tasks[0]
        checkpoint = self._repository.get_latest_checkpoint(int(task["id"]))
        result = self._adapter.resume_sop(
            self._adapter_request(
                session_id,
                str(task["sop_id"]),
                task=task,
                checkpoint_row=checkpoint,
                collected=dict(task.get("business_refs") or {}),
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
        saved = dict(collected or {})
        if checkpoint is not None:
            saved = dict(checkpoint.collected)
        return SopExecutionRequest(
            runtime_session_id=session_id,
            runtime_task_id=int(task["id"]) if task is not None else None,
            sop_id=sop_id,
            message=message,
            checkpoint=checkpoint,
            collected=saved,
            business_refs=dict(task.get("business_refs") or {}) if task is not None else {},
            metadata={"runtime": "runtime_lab"},
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
    return payload


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


def _scoped_variables(collected: dict[str, Any]) -> dict[str, Any]:
    return {f"conversation.{key}": value for key, value in collected.items()}


def _with_evidence(
    decision: RouteDecision,
    candidates: Sequence[RouteCandidate],
    stage: str,
    classifier_input: ClassifierInput | None = None,
    classifier_result: ClassifierResult | None = None,
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
        policy_gate={"stage": stage, "decisionAction": decision.action},
        classifier_request=classifier_input.to_dict() if classifier_input else None,
        classifier_result=classifier_result.to_dict() if classifier_result else None,
        handoff=decision.handoff,
        final_decision=_final_decision_payload(decision),
    )
