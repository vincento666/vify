from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from hashlib import sha256
import json
from math import ceil
import os
from pathlib import Path
import re
from time import perf_counter
from typing import Any

from app.modules.ai_assistant.domain.context_budget import (
    build_compaction_snapshot,
    context_window_from_context,
    estimate_context_budget,
)
from app.modules.ai_assistant.domain.live_model import LivePlannerConfig, LivePlannerDecision, QwenLivePlanner
from app.modules.ai_assistant.domain.memory_context import (
    active_working_memory_items,
    estimate_tokens as estimate_memory_tokens,
    load_instruction_memory,
    memory_payload_from_context,
    summary_from_context,
    upsert_session_summary,
)
from app.modules.ai_assistant.domain.observability import build_observability_snapshot
from app.modules.ai_assistant.domain.permissions import ApprovalMode, ApprovalPolicy, PermissionDecision
from app.modules.ai_assistant.domain.policy_runtime import SessionPermissionPolicy
from app.modules.ai_assistant.domain.plan_state import (
    complete_plan_without_execution,
    create_initial_plan_state,
    mark_plan_blocked,
    mark_plan_step_completed,
    mark_plan_step_started,
    normalize_planning_strategy,
    set_plan_final_result,
)
from app.modules.ai_assistant.domain.resource_lock import (
    ResourceLockAcquireResult,
    ResourceLockManager,
    ResourceLockMode,
    release_event,
)
from app.modules.ai_assistant.domain.sandbox import SandboxPolicy, SandboxVerdict
from app.modules.ai_assistant.domain.sandbox_runtime import SessionSandboxRuntime
from app.modules.ai_assistant.domain.scheduler import ScheduledToolInvocation, ToolScheduler
from app.modules.ai_assistant.domain.session_runtime import (
    RunControlConflict,
    apply_control_transition,
    build_run_checkpoint,
    request_payload_from_run,
    worker_claim_payload,
)
from app.modules.ai_assistant.domain.skills import SkillRuntime
from app.modules.ai_assistant.domain.streaming_runtime import stream_fallback_payload, text_delta_payload
from app.modules.ai_assistant.domain.tool_runtime import ToolRunner, ToolRunResult
from app.modules.ai_assistant.domain.trace_audit import build_trace_audit_export
from app.modules.ai_assistant.domain.tools import RiskLevel, ToolManifest, ToolRegistry, ToolResult
from app.modules.ai_assistant.infra.repository import AiAssistantRepository, IdempotencyConflict
from app.modules.chat.domain.llm_request import ChatRequestMessage


@dataclass(frozen=True)
class HarnessTurnResult:
    run: dict[str, Any]
    replayed: bool
    final_answer: str
    tool_calls: list[dict[str, Any]]
    approval_required: bool = False
    approval_id: int | None = None
    sandbox_denied: bool = False


@dataclass(frozen=True)
class ScheduledToolExecutionResult:
    recorded_tool_calls: list[dict[str, Any]]
    schedule: dict[str, Any]
    terminal_result: HarnessTurnResult | None = None


class AiAssistantHarnessService:
    def __init__(
        self,
        repository: AiAssistantRepository,
        tool_registry: ToolRegistry | None = None,
        approval_policy: ApprovalPolicy | None = None,
        sandbox_policy: SandboxPolicy | None = None,
        live_planner: QwenLivePlanner | None = None,
        tool_runner: ToolRunner | None = None,
        skill_runtime: SkillRuntime | None = None,
    ) -> None:
        self._repository = repository
        self._tools = tool_registry or ToolRegistry.with_builtin_tools()
        self._tool_runner = tool_runner or ToolRunner(self._tools, operation_ledger=repository)
        self._resource_locks = ResourceLockManager(repository)
        self._approval_policy = approval_policy or ApprovalPolicy(environment="test")
        self._sandbox_policy = sandbox_policy or SandboxPolicy()
        self._live_planner = live_planner
        self._skill_runtime = skill_runtime or SkillRuntime()

    def create_session(self, title: str = "", context: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._repository.create_session(title=title, context=context)

    def list_sessions(self) -> list[dict[str, Any]]:
        return self._repository.list_sessions()

    def get_session(self, session_id: int) -> dict[str, Any] | None:
        return self._repository.get_session(session_id)

    def clear_session_history(self, session_id: int) -> bool:
        return self._repository.clear_session_history(session_id)

    def delete_session(self, session_id: int) -> bool:
        return self._repository.delete_session(session_id)

    def run_message(
        self,
        session_id: int,
        message: str,
        idempotency_key: str | None = None,
        approval_mode: str = ApprovalMode.SMART_APPROVAL.value,
        planning_strategy: str | None = None,
        tool_name: str = "echo_context",
        tool_input: dict[str, Any] | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        model_mode: str = "deterministic",
        model_config: LivePlannerConfig | None = None,
        ai_assistant_budget: dict[str, Any] | None = None,
        model_budget_policy: dict[str, Any] | None = None,
    ) -> HarnessTurnResult:
        started = self.start_message(
            session_id=session_id,
            message=message,
            idempotency_key=idempotency_key,
            approval_mode=approval_mode,
            planning_strategy=planning_strategy,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_calls=tool_calls,
            model_mode=model_mode,
            model_config=model_config,
            ai_assistant_budget=ai_assistant_budget,
            model_budget_policy=model_budget_policy,
        )
        if started.replayed or started.run["status"] != "RUNNING":
            return started
        return self.complete_started_message(
            session_id=session_id,
            run_id=int(started.run["id"]),
            run=started.run,
            message=message,
            approval_mode=approval_mode,
            planning_strategy=planning_strategy,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_calls=tool_calls,
            model_mode=model_mode,
            model_config=model_config,
        )

    def start_message(
        self,
        *,
        session_id: int,
        message: str,
        idempotency_key: str | None = None,
        approval_mode: str = ApprovalMode.SMART_APPROVAL.value,
        planning_strategy: str | None = None,
        tool_name: str = "echo_context",
        tool_input: dict[str, Any] | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        model_mode: str = "deterministic",
        model_config: LivePlannerConfig | None = None,
        ai_assistant_budget: dict[str, Any] | None = None,
        model_budget_policy: dict[str, Any] | None = None,
    ) -> HarnessTurnResult:
        payload = tool_input or {"message": message}
        scheduled_tool_calls = _scheduled_tool_calls(tool_calls)
        strategy = normalize_planning_strategy(planning_strategy)
        budget_payload = dict(ai_assistant_budget or {})
        model_budget_policy_payload = dict(model_budget_policy or {})
        request_hash = _request_hash(
            {
                "message": message,
                "planningStrategy": strategy.value,
                "approvalMode": approval_mode,
                "toolName": tool_name,
                "toolInput": payload,
                "toolCalls": scheduled_tool_calls,
                "modelMode": model_mode,
                "modelConfig": _safe_model_config_payload(model_config),
                "aiAssistantBudget": budget_payload,
                "modelBudgetPolicy": model_budget_policy_payload,
            }
        )
        try:
            run, replayed = self._repository.create_or_replay_run(
                session_id=session_id,
                user_message=message,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
            )
        except IdempotencyConflict:
            raise
        if replayed:
            response = dict(run.get("response_payload") or {})
            return HarnessTurnResult(
                run=run,
                replayed=True,
                final_answer=str(response.get("finalAnswer") or ""),
                tool_calls=list(response.get("toolCalls") or []),
                approval_required=bool(response.get("approvalRequired") or False),
                approval_id=response.get("approvalId"),
                sandbox_denied=bool(response.get("sandboxDenied") or False),
            )

        run_id = int(run["id"])
        planned_tool_names = [call["toolName"] for call in scheduled_tool_calls]
        if not planned_tool_names and not _live_requested(model_mode):
            planned_tool_names = [tool_name]
        plan_state = create_initial_plan_state(
            run_id=run_id,
            message=message,
            requested_strategy=strategy.value,
            planned_tool_names=planned_tool_names,
        )
        context_state = self._build_memory_context_snapshot(
            session_id=session_id,
            run_id=run_id,
            message=message,
        )
        run = self._repository.update_run_input_payload(
            run_id,
            {
                "message": message,
                "planningStrategy": strategy.value,
                "approvalMode": approval_mode,
                "modelMode": model_mode,
                "plan": plan_state,
                "memory": context_state["memory"],
                "contextBudget": context_state["contextBudget"],
                "compactionSnapshot": context_state.get("compactionSnapshot"),
                "aiAssistantBudget": budget_payload,
                "modelBudgetPolicy": model_budget_policy_payload,
            },
        )
        self._repository.append_message(session_id, "user", message, run_id=run_id)
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="run.started",
            visible_title="运行开始",
            visible_summary="AI 助手运行已开始。",
            payload={"phase": "reason", "planningStrategy": strategy.value, "planId": plan_state["id"]},
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="plan.created",
            visible_title="计划已创建",
            visible_summary="AI 助手已创建结构化执行计划。",
            payload={"plan": plan_state},
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="task.created",
            visible_title="任务已创建",
            visible_summary="任务面板已绑定结构化计划。",
            payload={"planId": plan_state["id"], "planningStrategy": strategy.value},
        )
        if not _live_requested(model_mode):
            self._append_context_budget_events(
                run_id=run_id,
                session_id=session_id,
                context_state=context_state,
            )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="orchestration.phase_started",
            visible_title="推理规划",
            visible_summary="正在选择模型与工具编排路径。",
            payload={
                "phase": "reason",
                "promptLayers": [layer["name"] for layer in context_state["contextBudget"]["selectedLayers"]],
                "modelConfig": _safe_model_config_payload(model_config),
            },
        )
        return HarnessTurnResult(run=run, replayed=False, final_answer="", tool_calls=[])

    def queue_started_message(
        self,
        *,
        session_id: int,
        run_id: int,
        message: str,
        approval_mode: str = ApprovalMode.SMART_APPROVAL.value,
        planning_strategy: str | None = None,
        tool_name: str = "echo_context",
        tool_input: dict[str, Any] | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        model_mode: str = "deterministic",
        model_config: LivePlannerConfig | None = None,
        ai_assistant_budget: dict[str, Any] | None = None,
        model_budget_policy: dict[str, Any] | None = None,
    ) -> HarnessTurnResult:
        run = self._repository.get_run(run_id)
        if run is None:
            raise KeyError(f"AI Assistant run not found: {run_id}")
        if run["status"] != "RUNNING":
            return _turn_result_from_run(run)
        request = {
            "message": message,
            "approvalMode": approval_mode,
            "planningStrategy": planning_strategy,
            "toolName": tool_name,
            "toolInput": tool_input or {"message": message},
            "toolCalls": _scheduled_tool_calls(tool_calls),
            "modelMode": model_mode,
            "modelConfig": _safe_model_config_payload(model_config),
            "aiAssistantBudget": dict(ai_assistant_budget or {}),
            "modelBudgetPolicy": dict(model_budget_policy or {}),
        }
        queued = self._save_runtime_checkpoint(
            run_id=run_id,
            session_id=session_id,
            status="QUEUED",
            phase="queued",
            request=request,
            event_type="run.queued",
            visible_title="运行已入队",
            visible_summary="AI 助手运行已进入持久化队列。",
            emit_checkpoint_event=False,
        )
        return HarnessTurnResult(run=queued, replayed=False, final_answer="", tool_calls=[])

    def process_queued_run(
        self,
        run_id: int,
        *,
        model_config: LivePlannerConfig | None = None,
    ) -> HarnessTurnResult | None:
        run = self._repository.get_run(run_id)
        if run is None or run["status"] != "QUEUED":
            return None
        session_id = int(run["session_id"])
        request = request_payload_from_run(run)
        execution_model_config = _worker_execution_model_config(request, model_config)
        worker = worker_claim_payload()
        running = self._claim_queued_runtime_checkpoint(
            run_id=run_id,
            session_id=session_id,
            run=run,
            request=request,
            worker=worker,
        )
        if running is None:
            return None
        result = self.complete_started_message(
            session_id=session_id,
            run_id=run_id,
            run=running,
            message=str(request.get("message") or ""),
            approval_mode=str(request.get("approvalMode") or ApprovalMode.SMART_APPROVAL.value),
            planning_strategy=request.get("planningStrategy"),
            tool_name=str(request.get("toolName") or "echo_context"),
            tool_input=dict(request.get("toolInput") or {}),
            tool_calls=list(request.get("toolCalls") or []),
            model_mode=str(request.get("modelMode") or "deterministic"),
            model_config=execution_model_config,
        )
        completed_status = str(result.run.get("status") or "COMPLETED")
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="run.worker_heartbeat",
            visible_title="Worker 心跳",
            visible_summary="SessionRuntime worker 已完成一次处理心跳。",
            payload={"worker": worker, "checkpoint": _runtime_checkpoint_from_run(result.run)},
        )
        self._save_runtime_checkpoint(
            run_id=run_id,
            session_id=session_id,
            status=completed_status,
            phase=_runtime_phase_for_status(completed_status),
            request=request,
            worker=worker,
            event_type="run.checkpoint_saved",
            visible_title="运行检查点已保存",
            visible_summary="SessionRuntime 已保存运行恢复检查点。",
        )
        return result

    def _claim_queued_runtime_checkpoint(
        self,
        *,
        run_id: int,
        session_id: int,
        run: dict[str, Any],
        request: dict[str, Any],
        worker: dict[str, Any],
    ) -> dict[str, Any] | None:
        checkpoint = build_run_checkpoint(
            run_id=run_id,
            status="RUNNING",
            phase="worker_started",
            last_sequence=_last_event_sequence(self._repository, run_id),
            request=request,
            worker=worker,
        )
        input_payload = dict(run.get("input_payload") or {})
        existing_runtime = dict(input_payload.get("sessionRuntime") or {})
        input_payload["sessionRuntime"] = {
            **existing_runtime,
            "request": request,
            "checkpoint": checkpoint,
            "worker": worker,
        }
        claimed = self._repository.claim_run_status(
            run_id,
            expected_status="QUEUED",
            next_status="RUNNING",
            input_payload=input_payload,
        )
        if claimed is None:
            return None
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="run.worker_started",
            visible_title="运行 Worker 已启动",
            visible_summary="AI Assistant SessionRuntime worker 已领取该运行。",
            payload={"checkpoint": checkpoint, "worker": worker},
            status="RUNNING",
        )
        return claimed

    def pause_run(self, run_id: int, actor_id: str = "") -> dict[str, Any]:
        return self._control_run(run_id, action="pause", actor_id=actor_id)

    def resume_run(self, run_id: int, actor_id: str = "") -> dict[str, Any]:
        return self._control_run(run_id, action="resume", actor_id=actor_id)

    def cancel_run(self, run_id: int, actor_id: str = "") -> dict[str, Any]:
        return self._control_run(run_id, action="cancel", actor_id=actor_id)

    def _control_run(self, run_id: int, *, action: str, actor_id: str) -> dict[str, Any]:
        run = self._repository.get_run(run_id)
        if run is None:
            raise KeyError(f"AI Assistant run not found: {run_id}")
        session_id = int(run["session_id"])
        runtime = dict((run.get("input_payload") or {}).get("sessionRuntime") or {})
        transitioned = apply_control_transition({"status": run["status"]}, action=action, actor_id=actor_id)
        status = str(transitioned["status"])
        if status == run["status"]:
            raise RunControlConflict(f"Run {run_id} cannot {action} from status {run['status']}")
        response_payload = None
        completed = False
        if status == "CANCELLED":
            cancelled_approvals = self._repository.cancel_pending_approvals_for_run(
                run_id,
                actor_id,
                reason="run_cancelled",
            )
            cancelled_actions = self._repository.cancel_pending_proposed_actions_for_run(run_id)
            completed = True
            response_payload = {
                **dict(run.get("response_payload") or {}),
                "finalAnswer": "运行已取消。",
                "toolCalls": [],
                "approvalRequired": False,
                "approvalId": None,
                "sandboxDenied": False,
                "cancelledApprovals": cancelled_approvals,
                "cancelledProposedActions": cancelled_actions,
                "pendingToolCallsAfterApproval": [],
                "plan": _plan_payload_from_run(run),
            }
        updated = self._repository.update_run_status(
            run_id,
            status,
            response_payload=response_payload,
            completed=completed,
        )
        runtime["control"] = transitioned["control"]
        request = dict(runtime.get("request") or request_payload_from_run(run))
        checkpoint = build_run_checkpoint(
            run_id=run_id,
            status=status,
            phase=_runtime_phase_for_status(status),
            last_sequence=_last_event_sequence(self._repository, run_id),
            request=request,
            control=transitioned["control"],
        )
        input_payload = dict(updated.get("input_payload") or {})
        input_payload["sessionRuntime"] = {**runtime, "request": request, "checkpoint": checkpoint}
        updated = self._repository.update_run_input_payload(run_id, input_payload)
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type=_control_event_type(action),
            visible_title=_control_event_title(action),
            visible_summary=_control_event_summary(action),
            payload={"control": transitioned["control"], "checkpoint": checkpoint},
            status=status,
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="run.checkpoint_saved",
            visible_title="运行检查点已保存",
            visible_summary="SessionRuntime 已保存运行恢复检查点。",
            payload={"checkpoint": checkpoint},
            status=status,
        )
        return updated

    def _save_runtime_checkpoint(
        self,
        *,
        run_id: int,
        session_id: int,
        status: str,
        phase: str,
        request: dict[str, Any],
        event_type: str,
        visible_title: str,
        visible_summary: str,
        worker: dict[str, Any] | None = None,
        emit_checkpoint_event: bool = True,
    ) -> dict[str, Any]:
        run = self._repository.update_run_status(run_id, status)
        checkpoint = build_run_checkpoint(
            run_id=run_id,
            status=status,
            phase=phase,
            last_sequence=_last_event_sequence(self._repository, run_id),
            request=request,
            worker=worker,
        )
        input_payload = dict(run.get("input_payload") or {})
        existing_runtime = dict(input_payload.get("sessionRuntime") or {})
        input_payload["sessionRuntime"] = {
            **existing_runtime,
            "request": request,
            "checkpoint": checkpoint,
            "worker": worker or dict(existing_runtime.get("worker") or {}),
        }
        run = self._repository.update_run_input_payload(run_id, input_payload)
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type=event_type,
            visible_title=visible_title,
            visible_summary=visible_summary,
            payload={"checkpoint": checkpoint, "worker": worker or {}},
            status=status,
        )
        if emit_checkpoint_event and event_type != "run.checkpoint_saved":
            self._repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type="run.checkpoint_saved",
                visible_title="运行检查点已保存",
                visible_summary="SessionRuntime 已保存运行恢复检查点。",
                payload={"checkpoint": checkpoint},
                status=status,
            )
        return run

    def complete_started_message(
        self,
        *,
        session_id: int,
        run_id: int,
        run: dict[str, Any] | None = None,
        message: str,
        approval_mode: str = ApprovalMode.SMART_APPROVAL.value,
        planning_strategy: str | None = None,
        tool_name: str = "echo_context",
        tool_input: dict[str, Any] | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        model_mode: str = "deterministic",
        model_config: LivePlannerConfig | None = None,
    ) -> HarnessTurnResult:
        current_run = run or self._repository.get_run(run_id)
        if current_run is None:
            raise KeyError(f"AI Assistant run not found: {run_id}")
        payload = tool_input or {"message": message}
        scheduled_tool_calls = _scheduled_tool_calls(tool_calls)
        plan = _plan_payload_from_run(current_run)
        if plan.get("planningStrategy") == "plan_only":
            final_answer = "已生成计划，未执行工具。"
            plan = complete_plan_without_execution(plan, final_answer)
            current_run = self._persist_plan_state(run_id, plan)
            self._repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type="plan.step_completed",
                visible_title="计划步骤完成",
                visible_summary="plan_only 策略已完成计划生成。",
                payload={"planId": plan.get("id"), "step": plan.get("currentStep")},
            )
            self._append_task_updated(
                run_id=run_id,
                session_id=session_id,
                phase="plan_only_finalize",
                plan=plan,
            )
            cancelled = self._cancelled_turn_result(run_id, [])
            if cancelled is not None:
                return cancelled
            self._append_model_output_stream(
                run_id=run_id,
                session_id=session_id,
                model="deterministic",
                text=final_answer,
                phase="final_answer",
                source="harness_final_answer",
            )
            self._repository.append_message(session_id, "assistant", final_answer, run_id=run_id)
            completed = self._repository.complete_run(
                run_id,
                {
                    "finalAnswer": final_answer,
                    "toolCalls": [],
                    "approvalRequired": False,
                    "sandboxDenied": False,
                    "plan": plan,
                },
            )
            cancelled = self._cancelled_turn_result(run_id, [])
            if cancelled is not None:
                return cancelled
            self._repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type="task.completed",
                visible_title="任务完成",
                visible_summary="计划已生成，执行已按要求跳过。",
                payload={"planId": plan.get("id"), "finalResult": final_answer},
            )
            self._repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type="run.completed",
                visible_title="运行完成",
                visible_summary="AI 助手运行已完成。",
                payload={"finalAnswer": final_answer},
            )
            return HarnessTurnResult(run=completed, replayed=False, final_answer=final_answer, tool_calls=[])
        if _live_requested(model_mode) and self._planner_for(model_config) is not None:
            try:
                return self._run_live_react_loop(
                    run_id=run_id,
                    session_id=session_id,
                    run=current_run,
                    message=message,
                    approval_mode=approval_mode,
                    model_config=model_config,
                )
            except Exception as exc:  # pragma: no cover - exercised through API contracts
                return self._fail_run(
                    run_id=run_id,
                    session_id=session_id,
                    run=current_run,
                    reason=f"模型调用失败：{exc}",
                    payload={"provider": "openrouter", "model": (model_config.model if model_config else None)},
                )
        if _live_requested(model_mode):
            return self._fail_run(
                run_id=run_id,
                session_id=session_id,
                run=current_run,
                reason="live 模式未配置 OpenRouter Qwen 模型凭据。",
                payload={"modelMode": model_mode},
            )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="model.call_completed",
            visible_title="模型决策",
            visible_summary="本地确定性规划器已选择计划工具。"
            if scheduled_tool_calls
            else "本地确定性规划器已选择上下文回显工具。",
            payload={"toolNames": [call["toolName"] for call in scheduled_tool_calls]}
            if scheduled_tool_calls
            else {"toolName": "echo_context"},
        )
        self._append_task_updated(
            run_id=run_id,
            session_id=session_id,
            phase="deterministic_planning",
            current_tool=scheduled_tool_calls[0]["toolName"] if scheduled_tool_calls else tool_name,
        )
        if scheduled_tool_calls:
            return self._run_scheduled_tool_calls(
                session_id=session_id,
                run_id=run_id,
                run=current_run,
                message=message,
                approval_mode=approval_mode,
                tool_calls=scheduled_tool_calls,
            )
        manifest, gate_result, sandbox_runtime = self._evaluate_tool_security(
            run_id=run_id,
            session_id=session_id,
            approval_mode=approval_mode,
            tool_name=tool_name,
            payload=payload,
        )
        if gate_result is not None:
            return gate_result
        acquired_locks, lock_result = self._acquire_tool_resource_locks(
            run_id=run_id,
            session_id=session_id,
            manifest=manifest,
            payload=payload,
            tool_name=tool_name,
        )
        if lock_result is not None:
            return lock_result
        started_step = self._mark_plan_step_started(run_id, tool_name)
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="plan.step_started",
            visible_title="计划步骤开始",
            visible_summary=f"{_tool_label(tool_name)} 已开始。",
            payload={"toolName": tool_name, "step": started_step},
        )
        self._append_task_updated(
            run_id=run_id,
            session_id=session_id,
            phase="tool_execution",
            current_tool=tool_name,
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="tool.call_started",
            visible_title="工具开始",
            visible_summary=f"{_tool_label(tool_name)} 已开始执行。",
            payload={"toolName": tool_name, "input": payload},
        )
        dispatch_result = self._dispatch_tool(
            run_id=run_id,
            session_id=session_id,
            message=message,
            tool_name=tool_name,
            payload=payload,
            sandbox_runtime=sandbox_runtime,
        )
        self._annotate_tool_result_with_locks(dispatch_result, acquired_locks)
        tool_result = dispatch_result["tool_result"]
        duration_ms = int(dispatch_result["duration_ms"])
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="tool.call_output",
            visible_title="工具输出",
            visible_summary=_tool_result_visible_summary(tool_result.output),
            payload={"toolName": tool_name, "output": tool_result.output},
        )
        tool_call = self._repository.record_tool_call(
            run_id=run_id,
            session_id=session_id,
            tool_name=tool_name,
            input_payload=_tool_record_input(payload, dispatch_result=dispatch_result),
            output_payload=tool_result.output,
            status=tool_result.status,
            duration_ms=duration_ms,
        )
        self._append_tool_runtime_events(
            run_id=run_id,
            session_id=session_id,
            tool_name=tool_name,
            dispatch_result=dispatch_result,
            tool_call_id=int(tool_call["id"]),
        )
        self._release_tool_resource_locks(
            run_id=run_id,
            session_id=session_id,
            acquired_locks=acquired_locks,
        )
        tool_call_payload = _tool_call_payload(tool_call)
        if _tool_call_failed_with_observation(tool_call_payload):
            self._append_tool_call_failed_event(
                run_id=run_id,
                session_id=session_id,
                tool_name=tool_name,
                tool_call_payload=tool_call_payload,
                tool_call_id=int(tool_call["id"]),
            )
            return self._recover_or_finalize_failed_tool_observation(
                run_id=run_id,
                session_id=session_id,
                tool_name=tool_name,
                tool_call=tool_call_payload,
                original_payload=payload,
                approval_mode=approval_mode,
            )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="tool.call_completed",
            visible_title="工具完成",
            visible_summary=f"{_tool_label(tool_name)} 已完成。",
            payload={"toolName": tool_name, "status": tool_result.status},
            tool_call_id=int(tool_call["id"]),
        )
        final_answer = _tool_execution_answer([tool_call_payload])
        completed_step = self._mark_plan_step_completed(run_id, tool_name, final_answer)
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="plan.step_completed",
            visible_title="计划步骤完成",
            visible_summary=f"{_tool_label(tool_name)} 已完成。",
            payload={"toolName": tool_name, "step": completed_step},
        )
        self._append_task_updated(
            run_id=run_id,
            session_id=session_id,
            phase="tool_observation",
            current_tool=tool_name,
        )
        cancelled = self._cancelled_turn_result(run_id, [tool_call_payload])
        if cancelled is not None:
            return cancelled
        self._append_model_output_stream(
            run_id=run_id,
            session_id=session_id,
            model="deterministic",
            text=final_answer,
            phase="final_answer",
            source="harness_final_answer",
        )
        self._repository.append_message(session_id, "assistant", final_answer, run_id=run_id)
        plan = _plan_payload_from_run(self._repository.get_run(run_id) or {})
        response_payload = {
            "finalAnswer": final_answer,
            "toolCalls": [tool_call_payload],
            "approvalRequired": False,
            "sandboxDenied": False,
            "plan": plan,
        }
        completed = self._repository.complete_run(run_id, response_payload)
        cancelled = self._cancelled_turn_result(run_id, [tool_call_payload])
        if cancelled is not None:
            return cancelled
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="task.completed",
            visible_title="任务完成",
            visible_summary="结构化计划已执行完成。",
            payload={"planId": plan.get("id"), "finalResult": final_answer},
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="run.completed",
            visible_title="运行完成",
            visible_summary="AI 助手运行已完成。",
            payload={"finalAnswer": final_answer},
        )
        self._update_session_summary_after_run(
            session_id=session_id,
            run_id=run_id,
            user_message=message,
            final_answer=final_answer,
        )
        return HarnessTurnResult(
            run=completed,
            replayed=False,
            final_answer=final_answer,
            tool_calls=[tool_call_payload],
        )

    def _planner_for(self, model_config: LivePlannerConfig | None) -> QwenLivePlanner | None:
        if model_config is None:
            return self._live_planner
        if self._live_planner is not None:
            return self._live_planner.with_config(model_config)
        if not model_config.api_key and not model_config.api_key_ref:
            return None
        return QwenLivePlanner(model_config)

    def _plan_with_live_model(
        self,
        *,
        run_id: int,
        session_id: int,
        message: str,
        model_config: LivePlannerConfig | None = None,
        messages: list[ChatRequestMessage] | None = None,
        round_index: int = 1,
    ) -> LivePlannerDecision:
        planner = self._planner_for(model_config)
        if planner is None:
            raise RuntimeError("AI Assistant live planner is not configured")
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="model.call_started",
            visible_title="模型调用开始",
            visible_summary=f"正在调用 OpenRouter {planner.model}。",
            payload={"provider": "openrouter", "model": planner.model, "roundIndex": round_index},
        )
        streamed_count = 0

        def append_stream_chunk(chunk: str, index: int) -> None:
            nonlocal streamed_count
            if self._run_is_cancelled(run_id):
                return
            streamed_count = max(streamed_count, index)
            self._repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type="text.delta",
                visible_title="实时输出",
                visible_summary=chunk,
                payload=text_delta_payload(
                    index=index,
                    delta=chunk,
                    model=planner.model,
                    round_index=round_index,
                    source="openrouter_delta",
                ),
            )
            self._repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type="model.stream_chunk",
                visible_title="流式输出",
                visible_summary=chunk,
                payload={
                    "index": index,
                    "chunk": chunk,
                    "model": planner.model,
                    "roundIndex": round_index,
                    "streaming": True,
                    "source": "openrouter_delta",
                },
            )

        decision = (
            planner.plan_messages(messages, self._tools, on_stream_chunk=append_stream_chunk)
            if messages is not None
            else planner.plan(message, self._tools, on_stream_chunk=append_stream_chunk)
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="model.thought_summary",
            visible_title="思考摘要",
            visible_summary=decision.thought_summary,
            payload={"model": decision.model, "summary": decision.thought_summary, "roundIndex": round_index},
        )
        if streamed_count == 0:
            self._repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type="stream.fallback",
                visible_title="流式降级",
                visible_summary="当前模型未提供原始 token 流，已切换为非流式回放。",
                payload=stream_fallback_payload(model=decision.model, source=decision.stream_source),
            )
            for index, chunk in enumerate(decision.stream_chunks, start=1):
                self._repository.append_event(
                    run_id=run_id,
                    session_id=session_id,
                    event_type="model.stream_chunk",
                    visible_title="流式输出",
                    visible_summary=chunk,
                    payload={
                        "index": index,
                        "chunk": chunk,
                        "model": decision.model,
                        "roundIndex": round_index,
                        "streaming": decision.streaming,
                        "source": decision.stream_source,
                    },
                )
        supplemented_tool_calls = _supplement_required_tool_calls(message, decision.tool_calls)
        if supplemented_tool_calls != decision.tool_calls:
            decision = LivePlannerDecision(
                final_answer=decision.final_answer,
                thought_summary=decision.thought_summary,
                stream_chunks=decision.stream_chunks,
                tool_calls=supplemented_tool_calls,
                usage=decision.usage,
                model=decision.model,
                provider=decision.provider,
                streaming=decision.streaming,
                stream_source=decision.stream_source,
            )
        tool_names = [call["toolName"] for call in decision.tool_calls]
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="model.tool_call_decision",
            visible_title="工具调用决策",
            visible_summary="模型已选择工具调用。" if tool_names else "模型未选择工具调用。",
            payload={"toolNames": tool_names, "model": decision.model, "usage": decision.usage, "roundIndex": round_index},
        )
        file_tools = [name for name in tool_names if name in {"read_workspace_file", "write_workspace_file"}]
        if file_tools:
            self._repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type="model.file_intent",
                visible_title="文件操作意图",
                visible_summary="模型规划了文件读取或写入动作。",
                payload={"toolNames": file_tools},
            )
        skill_tools = [name for name in tool_names if name == "invoke_skill"]
        if skill_tools:
            self._repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type="model.skill_intent",
                visible_title="技能调用意图",
                visible_summary="模型记录了技能调用意图；当前 harness 不执行本机 Codex skill。",
                payload={"toolNames": skill_tools, "execution": "intent_recorded"},
            )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="task.updated",
            visible_title="任务编排",
            visible_summary="任务面板已记录模型规划、工具调用和审批状态。",
            payload={"phase": "live_model_planning", "toolNames": tool_names, "roundIndex": round_index},
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="model.call_completed",
            visible_title="模型调用完成",
            visible_summary=f"OpenRouter {decision.model} 已返回规划结果。",
            payload={"provider": decision.provider, "model": decision.model, "usage": decision.usage, "roundIndex": round_index},
        )
        return decision

    def _run_live_react_loop(
        self,
        *,
        run_id: int,
        session_id: int,
        run: dict[str, Any],
        message: str,
        approval_mode: str,
        model_config: LivePlannerConfig | None,
    ) -> HarnessTurnResult:
        planner = self._planner_for(model_config)
        if planner is None:
            raise RuntimeError("AI Assistant live planner is not configured")
        messages = planner.initial_messages(message)
        decisions: list[LivePlannerDecision] = []
        recorded_tool_calls: list[dict[str, Any]] = []
        seen_tool_keys: set[str] = set()
        written_paths: set[str] = set()
        read_after_write_keys: set[str] = set()

        for round_index in range(1, 5):
            decision = self._plan_with_live_model(
                run_id=run_id,
                session_id=session_id,
                message=message,
                model_config=model_config,
                messages=messages,
                round_index=round_index,
            )
            decisions.append(decision)
            if not decision.tool_calls:
                return self._complete_live_run(
                    run_id=run_id,
                    session_id=session_id,
                    run=run,
                    final_answer=decision.final_answer or "模型未选择工具，已完成回复。",
                    recorded_tool_calls=recorded_tool_calls,
                    decision=decision,
                    decisions=decisions,
                    append_final_stream=False,
                )

            written_paths.update(_written_workspace_paths(recorded_tool_calls))
            new_tool_calls = _new_live_tool_calls(
                decision.tool_calls,
                seen_tool_keys=seen_tool_keys,
                written_paths=written_paths,
                read_after_write_keys=read_after_write_keys,
            )
            if not new_tool_calls:
                final_answer = decision.final_answer or _tool_execution_answer(recorded_tool_calls)
                return self._complete_live_run(
                    run_id=run_id,
                    session_id=session_id,
                    run=run,
                    final_answer=final_answer,
                    recorded_tool_calls=recorded_tool_calls,
                    decision=decision,
                    decisions=decisions,
                    append_final_stream=True,
                )

            seen_tool_keys.update(_tool_call_key(call) for call in new_tool_calls)
            execution = self._execute_scheduled_tool_calls(
                session_id=session_id,
                run_id=run_id,
                message=message,
                approval_mode=approval_mode,
                tool_calls=new_tool_calls,
                failed_observation_mode="replan",
            )
            recorded_tool_calls.extend(execution.recorded_tool_calls)
            if execution.terminal_result is not None:
                return self._with_accumulated_tool_calls(execution.terminal_result, recorded_tool_calls)
            written_paths.update(_written_workspace_paths(execution.recorded_tool_calls))
            messages = _react_messages_after_tools(messages, decision, new_tool_calls, execution.recorded_tool_calls)

        last_decision = decisions[-1]
        final_answer = last_decision.final_answer or _tool_execution_answer(recorded_tool_calls)
        return self._complete_live_run(
            run_id=run_id,
            session_id=session_id,
            run=run,
            final_answer=final_answer,
            recorded_tool_calls=recorded_tool_calls,
            decision=last_decision,
            decisions=decisions,
            append_final_stream=True,
        )

    def _complete_live_run(
        self,
        *,
        run_id: int,
        session_id: int,
        run: dict[str, Any],
        final_answer: str,
        recorded_tool_calls: list[dict[str, Any]],
        decision: LivePlannerDecision,
        decisions: list[LivePlannerDecision],
        append_final_stream: bool,
    ) -> HarnessTurnResult:
        cancelled = self._cancelled_run_result(run_id)
        if cancelled is not None:
            return HarnessTurnResult(
                run=cancelled,
                replayed=False,
                final_answer=str((cancelled.get("response_payload") or {}).get("finalAnswer") or "运行已取消。"),
                tool_calls=recorded_tool_calls,
            )
        if append_final_stream:
            self._append_model_output_stream(
                run_id=run_id,
                session_id=session_id,
                model=decision.model,
                text=final_answer,
                phase="final_answer",
                source="harness_final_answer",
            )
        self._repository.append_message(session_id, "assistant", final_answer, run_id=run_id)
        plan = set_plan_final_result(_plan_payload_from_run(self._repository.get_run(run_id) or {}), final_answer)
        self._persist_plan_state(run_id, plan)
        response_payload = {
            "finalAnswer": final_answer,
            "toolCalls": recorded_tool_calls,
            "approvalRequired": False,
            "sandboxDenied": False,
            "model": {"provider": decision.provider, "model": decision.model, "usage": _merged_usage(decisions)},
            "plan": plan,
        }
        completed = self._repository.complete_run(run_id, response_payload)
        cancelled = self._cancelled_turn_result(run_id, recorded_tool_calls)
        if cancelled is not None:
            return cancelled
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="task.completed",
            visible_title="任务完成",
            visible_summary="结构化计划已执行完成。",
            payload={"planId": plan.get("id"), "finalResult": final_answer},
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="run.completed",
            visible_title="运行完成",
            visible_summary="AI 助手运行已完成。",
            payload={"finalAnswer": final_answer},
        )
        self._append_persisted_context_budget_events(
            run_id=run_id,
            session_id=session_id,
            run=completed or run,
        )
        self._update_session_summary_after_run(
            session_id=session_id,
            run_id=run_id,
            user_message=str(((completed or run).get("input_payload") or {}).get("message") or ""),
            final_answer=final_answer,
        )
        return HarnessTurnResult(
            run=completed or run,
            replayed=False,
            final_answer=final_answer,
            tool_calls=recorded_tool_calls,
        )

    def _run_is_cancelled(self, run_id: int) -> bool:
        run = self._repository.get_run(run_id)
        return run is not None and run.get("status") == "CANCELLED"

    def _cancelled_run_result(self, run_id: int) -> dict[str, Any] | None:
        run = self._repository.get_run(run_id)
        if run is None or run.get("status") != "CANCELLED":
            return None
        return run

    def _cancelled_turn_result(
        self,
        run_id: int,
        recorded_tool_calls: list[dict[str, Any]],
    ) -> HarnessTurnResult | None:
        cancelled = self._cancelled_run_result(run_id)
        if cancelled is None:
            return None
        response = dict(cancelled.get("response_payload") or {})
        return HarnessTurnResult(
            run=cancelled,
            replayed=False,
            final_answer=str(response.get("finalAnswer") or "运行已取消。"),
            tool_calls=recorded_tool_calls,
        )

    def _with_accumulated_tool_calls(
        self,
        result: HarnessTurnResult,
        recorded_tool_calls: list[dict[str, Any]],
    ) -> HarnessTurnResult:
        response_payload = dict(result.run.get("response_payload") or {})
        response_payload["toolCalls"] = recorded_tool_calls
        updated = self._repository.complete_run(
            int(result.run["id"]),
            response_payload,
            status=str(result.run["status"]),
        )
        return HarnessTurnResult(
            run=updated or result.run,
            replayed=result.replayed,
            final_answer=result.final_answer,
            tool_calls=recorded_tool_calls,
            approval_required=result.approval_required,
            approval_id=result.approval_id,
            sandbox_denied=result.sandbox_denied,
        )

    def _fail_run(
        self,
        *,
        run_id: int,
        session_id: int,
        run: dict[str, Any],
        reason: str,
        payload: dict[str, Any] | None = None,
    ) -> HarnessTurnResult:
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="model.call_failed",
            visible_title="模型调用失败",
            visible_summary=reason,
            payload=payload or {},
            status="FAILED",
            level="error",
        )
        plan = self._mark_plan_blocked(run_id, session_id, reason, status="FAILED")
        failed = self._repository.complete_run(
            run_id,
            {
                "finalAnswer": reason,
                "toolCalls": [],
                "approvalRequired": False,
                "sandboxDenied": False,
                "plan": plan,
            },
            status="FAILED",
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="run.failed",
            visible_title="运行失败",
            visible_summary=reason,
            payload={"finalAnswer": reason},
            status="FAILED",
            level="error",
        )
        return HarnessTurnResult(run=failed or run, replayed=False, final_answer=reason, tool_calls=[])

    def _append_model_output_stream(
        self,
        *,
        run_id: int,
        session_id: int,
        model: str,
        text: str,
        phase: str,
        source: str,
    ) -> None:
        for index, chunk in enumerate(_text_chunks(text), start=1):
            self._repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type="text.delta",
                visible_title="实时输出",
                visible_summary=chunk,
                payload=text_delta_payload(
                    index=index,
                    delta=chunk,
                    model=model,
                    phase=phase,
                    source=source,
                    streaming=False,
                    raw=False,
                    synthetic=True,
                ),
            )
            self._repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type="model.stream_chunk",
                visible_title="模型输出",
                visible_summary=chunk,
                payload={
                    "index": index,
                    "chunk": chunk,
                    "model": model,
                    "phase": phase,
                    "streaming": False,
                    "raw": False,
                    "synthetic": True,
                    "source": source,
                },
            )

    def _run_scheduled_tool_calls(
        self,
        *,
        session_id: int,
        run_id: int,
        run: dict[str, Any],
        message: str,
        approval_mode: str,
        tool_calls: list[dict[str, Any]],
        model_decision: LivePlannerDecision | None = None,
    ) -> HarnessTurnResult:
        execution = self._execute_scheduled_tool_calls(
            session_id=session_id,
            run_id=run_id,
            message=message,
            approval_mode=approval_mode,
            tool_calls=tool_calls,
        )
        if execution.terminal_result is not None:
            return self._with_accumulated_tool_calls(execution.terminal_result, execution.recorded_tool_calls)
        return self._complete_tool_run(
            session_id=session_id,
            run_id=run_id,
            run=run,
            recorded_tool_calls=execution.recorded_tool_calls,
            schedule=execution.schedule,
            model_decision=model_decision,
        )

    def _execute_scheduled_tool_calls(
        self,
        *,
        session_id: int,
        run_id: int,
        message: str,
        approval_mode: str,
        tool_calls: list[dict[str, Any]],
        failed_observation_mode: str = "recover",
    ) -> ScheduledToolExecutionResult:
        invocations = [
            ScheduledToolInvocation(str(call["toolName"]), dict(call.get("toolInput") or {}))
            for call in tool_calls
        ]
        plan = ToolScheduler(self._tools).plan(invocations, context={"session_id": session_id})
        recorded_tool_calls: list[dict[str, Any]] = []
        for batch_index, batch in enumerate(plan.batches):
            self._repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type="scheduler.batch_started",
                visible_title="工具批次开始",
                visible_summary=f"{batch.execution_mode} 批次 {batch.batch_id} 已开始。",
                payload={
                    "batchId": batch.batch_id,
                    "executionMode": batch.execution_mode,
                    "toolNames": [item.tool_name for item in batch.items],
                    "readResources": batch.read_resources,
                    "writeResources": batch.write_resources,
                    "lockMode": batch.lock_mode,
                    "resourceLockReason": batch.resource_lock_reason,
                    "parallelEligible": batch.parallel_eligible,
                },
            )
            if batch.execution_mode == "READ_PARALLEL" and len(batch.items) > 1:
                parallel_result = self._run_read_parallel_batch(
                    session_id=session_id,
                    run_id=run_id,
                    message=message,
                    approval_mode=approval_mode,
                    batch=batch,
                    failed_observation_mode=failed_observation_mode,
                )
                if isinstance(parallel_result, HarnessTurnResult):
                    return ScheduledToolExecutionResult(
                        recorded_tool_calls=parallel_result.tool_calls or recorded_tool_calls,
                        schedule=_schedule_payload(plan),
                        terminal_result=parallel_result,
                    )
                recorded_tool_calls.extend(parallel_result)
            else:
                for index, item in enumerate(batch.items):
                    pending_tool_calls = _remaining_scheduled_tool_calls(plan.batches, batch_index, index)
                    result = self._run_scheduled_tool_call(
                        session_id=session_id,
                        run_id=run_id,
                        message=message,
                        approval_mode=approval_mode,
                        tool_name=item.tool_name,
                        payload=item.tool_input,
                        scheduler_metadata=batch.item_metadata[index],
                        pending_tool_calls_after_approval=pending_tool_calls,
                        failed_observation_mode=failed_observation_mode,
                    )
                    if isinstance(result, HarnessTurnResult):
                        return ScheduledToolExecutionResult(
                            recorded_tool_calls=result.tool_calls or recorded_tool_calls,
                            schedule=_schedule_payload(plan),
                            terminal_result=result,
                        )
                    recorded_tool_calls.append(result)
            self._repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type="scheduler.batch_completed",
                visible_title="工具批次完成",
                visible_summary=f"{batch.execution_mode} 批次 {batch.batch_id} 已完成。",
                payload={
                    "batchId": batch.batch_id,
                    "executionMode": batch.execution_mode,
                    "toolCallCount": len(batch.items),
                    "lockMode": batch.lock_mode,
                },
            )
        return ScheduledToolExecutionResult(
            recorded_tool_calls=recorded_tool_calls,
            schedule=_schedule_payload(plan),
        )

    def _complete_tool_run(
        self,
        *,
        session_id: int,
        run_id: int,
        run: dict[str, Any],
        recorded_tool_calls: list[dict[str, Any]],
        schedule: dict[str, Any],
        model_decision: LivePlannerDecision | None = None,
    ) -> HarnessTurnResult:
        final_answer = _tool_execution_answer(recorded_tool_calls)
        if model_decision and model_decision.final_answer:
            final_answer = f"{model_decision.final_answer}\n\n{final_answer}"
        cancelled = self._cancelled_turn_result(run_id, recorded_tool_calls)
        if cancelled is not None:
            return cancelled
        self._append_model_output_stream(
            run_id=run_id,
            session_id=session_id,
            model=model_decision.model if model_decision else "deterministic",
            text=final_answer,
            phase="final_answer",
            source="harness_final_answer",
        )
        self._repository.append_message(session_id, "assistant", final_answer, run_id=run_id)
        plan = set_plan_final_result(_plan_payload_from_run(self._repository.get_run(run_id) or {}), final_answer)
        self._persist_plan_state(run_id, plan)
        response_payload = {
            "finalAnswer": final_answer,
            "toolCalls": recorded_tool_calls,
            "approvalRequired": False,
            "sandboxDenied": False,
            "model": (
                {"provider": model_decision.provider, "model": model_decision.model, "usage": model_decision.usage}
                if model_decision
                else None
            ),
            "schedule": schedule,
            "plan": plan,
        }
        completed = self._repository.complete_run(run_id, response_payload)
        cancelled = self._cancelled_turn_result(run_id, recorded_tool_calls)
        if cancelled is not None:
            return cancelled
        self._append_task_updated(
            run_id=run_id,
            session_id=session_id,
            phase="finalize",
            plan=plan,
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="task.completed",
            visible_title="任务完成",
            visible_summary="结构化计划已执行完成。",
            payload={"planId": plan.get("id"), "finalResult": final_answer},
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="run.completed",
            visible_title="运行完成",
            visible_summary="AI 助手运行已完成。",
            payload={"finalAnswer": final_answer},
        )
        return HarnessTurnResult(
            run=completed or run,
            replayed=False,
            final_answer=final_answer,
            tool_calls=recorded_tool_calls,
        )

    def _run_read_parallel_batch(
        self,
        *,
        session_id: int,
        run_id: int,
        message: str,
        approval_mode: str,
        batch: Any,
        failed_observation_mode: str = "recover",
    ) -> list[dict[str, Any]] | HarnessTurnResult:
        acquired_locks_by_index: list[list[ResourceLockAcquireResult]] = []
        sandbox_runtimes_by_index: list[SessionSandboxRuntime] = []
        for index, item in enumerate(batch.items):
            manifest, gate_result, sandbox_runtime = self._evaluate_tool_security(
                run_id=run_id,
                session_id=session_id,
                approval_mode=approval_mode,
                tool_name=item.tool_name,
                payload=item.tool_input,
            )
            if gate_result is not None:
                for acquired in acquired_locks_by_index:
                    self._release_tool_resource_locks(run_id=run_id, session_id=session_id, acquired_locks=acquired)
                return gate_result
            acquired_locks, lock_result = self._acquire_tool_resource_locks(
                run_id=run_id,
                session_id=session_id,
                manifest=manifest,
                payload=item.tool_input,
                tool_name=item.tool_name,
            )
            if lock_result is not None:
                for acquired in acquired_locks_by_index:
                    self._release_tool_resource_locks(run_id=run_id, session_id=session_id, acquired_locks=acquired)
                return lock_result
            acquired_locks_by_index.append(acquired_locks)
            sandbox_runtimes_by_index.append(sandbox_runtime)
            started_step = self._mark_plan_step_started(run_id, item.tool_name)
            self._repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type="plan.step_started",
                visible_title="计划步骤开始",
                visible_summary=f"{_tool_label(item.tool_name)} 已开始。",
                payload={"toolName": item.tool_name, "step": started_step},
            )
            self._append_task_updated(
                run_id=run_id,
                session_id=session_id,
                phase="tool_execution",
                current_tool=item.tool_name,
            )
            self._repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type="tool.call_started",
                visible_title="工具开始",
                visible_summary=f"{_tool_label(item.tool_name)} 已开始执行。",
                payload={
                    "toolName": item.tool_name,
                    "input": item.tool_input,
                    "scheduler": batch.item_metadata[index],
                },
                correlation_ids={"scheduler": batch.item_metadata[index]},
            )
        with ThreadPoolExecutor(max_workers=max(1, len(batch.items))) as executor:
            futures = [
                executor.submit(
                    self._dispatch_tool,
                    run_id=run_id,
                    session_id=session_id,
                    message=message,
                    tool_name=item.tool_name,
                    payload=item.tool_input,
                    sandbox_runtime=sandbox_runtimes_by_index[index],
                )
                for index, item in enumerate(batch.items)
            ]
            dispatch_results = [future.result() for future in futures]

        recorded: list[dict[str, Any]] = []
        first_failed_tool: tuple[str, dict[str, Any]] | None = None
        for index, (item, dispatch_result) in enumerate(zip(batch.items, dispatch_results, strict=True)):
            scheduler_metadata = batch.item_metadata[index]
            self._annotate_tool_result_with_locks(dispatch_result, acquired_locks_by_index[index])
            tool_result = dispatch_result["tool_result"]
            self._repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type="tool.call_output",
                visible_title="工具输出",
                visible_summary=_tool_result_visible_summary(tool_result.output),
                payload={"toolName": item.tool_name, "output": tool_result.output, "scheduler": scheduler_metadata},
                correlation_ids={"scheduler": scheduler_metadata},
            )
            tool_call = self._repository.record_tool_call(
                run_id=run_id,
                session_id=session_id,
                tool_name=item.tool_name,
                input_payload=_tool_record_input(
                    item.tool_input,
                    dispatch_result=dispatch_result,
                    extra={"_scheduler": scheduler_metadata},
                ),
                output_payload=tool_result.output,
                status=tool_result.status,
                duration_ms=int(dispatch_result["duration_ms"]),
            )
            self._append_tool_runtime_events(
                run_id=run_id,
                session_id=session_id,
                tool_name=item.tool_name,
                dispatch_result=dispatch_result,
                tool_call_id=int(tool_call["id"]),
                scheduler_metadata=scheduler_metadata,
            )
            self._release_tool_resource_locks(
                run_id=run_id,
                session_id=session_id,
                acquired_locks=acquired_locks_by_index[index],
            )
            tool_call_payload = _tool_call_payload(tool_call)
            if _tool_call_failed_with_observation(tool_call_payload):
                self._append_tool_call_failed_event(
                    run_id=run_id,
                    session_id=session_id,
                    tool_name=item.tool_name,
                    tool_call_payload=tool_call_payload,
                    tool_call_id=int(tool_call["id"]),
                    scheduler_metadata=scheduler_metadata,
                )
                recorded.append(tool_call_payload)
                if first_failed_tool is None:
                    first_failed_tool = (item.tool_name, tool_call_payload)
                continue
            self._repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type="tool.call_completed",
                visible_title="工具完成",
                visible_summary=f"{_tool_label(item.tool_name)} 已完成。",
                payload={"toolName": item.tool_name, "status": tool_result.status, "scheduler": scheduler_metadata},
                tool_call_id=int(tool_call["id"]),
                correlation_ids={"scheduler": scheduler_metadata},
            )
            completed_step = self._mark_plan_step_completed(run_id, item.tool_name)
            self._repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type="plan.step_completed",
                visible_title="计划步骤完成",
                visible_summary=f"{_tool_label(item.tool_name)} 已完成。",
                payload={"toolName": item.tool_name, "step": completed_step},
            )
            self._append_task_updated(
                run_id=run_id,
                session_id=session_id,
                phase="tool_observation",
                current_tool=item.tool_name,
            )
            recorded.append(tool_call_payload)
        if first_failed_tool is not None:
            failed_tool_name, failed_tool_call = first_failed_tool
            if failed_observation_mode == "replan":
                self._append_failed_observation_forwarded_for_replan(
                    run_id=run_id,
                    session_id=session_id,
                    tool_name=failed_tool_name,
                    tool_call=failed_tool_call,
                    phase="read_parallel_failed_observation_replan",
                )
                return recorded
            return self._recover_or_finalize_failed_tool_observation(
                run_id=run_id,
                session_id=session_id,
                tool_name=failed_tool_name,
                tool_call=failed_tool_call,
                original_payload=dict(failed_tool_call.get("input") or {}),
                approval_mode=approval_mode,
                task_phase="read_parallel_failed_observation",
            )
        return recorded

    def _run_scheduled_tool_call(
        self,
        *,
        session_id: int,
        run_id: int,
        message: str,
        approval_mode: str,
        tool_name: str,
        payload: dict[str, Any],
        scheduler_metadata: dict[str, Any],
        pending_tool_calls_after_approval: list[dict[str, Any]] | None = None,
        failed_observation_mode: str = "recover",
    ) -> dict[str, Any] | HarnessTurnResult:
        manifest, gate_result, sandbox_runtime = self._evaluate_tool_security(
            run_id=run_id,
            session_id=session_id,
            approval_mode=approval_mode,
            tool_name=tool_name,
            payload=payload,
            pending_tool_calls_after_approval=pending_tool_calls_after_approval,
        )
        if gate_result is not None:
            return gate_result
        acquired_locks, lock_result = self._acquire_tool_resource_locks(
            run_id=run_id,
            session_id=session_id,
            manifest=manifest,
            payload=payload,
            tool_name=tool_name,
        )
        if lock_result is not None:
            return lock_result
        started_step = self._mark_plan_step_started(run_id, tool_name)
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="plan.step_started",
            visible_title="计划步骤开始",
            visible_summary=f"{_tool_label(tool_name)} 已开始。",
            payload={"toolName": tool_name, "step": started_step},
        )
        self._append_task_updated(
            run_id=run_id,
            session_id=session_id,
            phase="tool_execution",
            current_tool=tool_name,
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="tool.call_started",
            visible_title="工具开始",
            visible_summary=f"{_tool_label(tool_name)} 已开始执行。",
            payload={"toolName": tool_name, "input": payload, "scheduler": scheduler_metadata},
            correlation_ids={"scheduler": scheduler_metadata},
        )
        dispatch_result = self._dispatch_tool(
            run_id=run_id,
            session_id=session_id,
            message=message,
            tool_name=tool_name,
            payload=payload,
            sandbox_runtime=sandbox_runtime,
        )
        self._annotate_tool_result_with_locks(dispatch_result, acquired_locks)
        tool_result = dispatch_result["tool_result"]
        duration_ms = int(dispatch_result["duration_ms"])
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="tool.call_output",
            visible_title="工具输出",
            visible_summary=_tool_result_visible_summary(tool_result.output),
            payload={"toolName": tool_name, "output": tool_result.output, "scheduler": scheduler_metadata},
            correlation_ids={"scheduler": scheduler_metadata},
        )
        tool_call = self._repository.record_tool_call(
            run_id=run_id,
            session_id=session_id,
            tool_name=tool_name,
            input_payload=_tool_record_input(
                payload,
                dispatch_result=dispatch_result,
                extra={"_scheduler": scheduler_metadata},
            ),
            output_payload=tool_result.output,
            status=tool_result.status,
            duration_ms=duration_ms,
        )
        self._append_tool_runtime_events(
            run_id=run_id,
            session_id=session_id,
            tool_name=tool_name,
            dispatch_result=dispatch_result,
            tool_call_id=int(tool_call["id"]),
            scheduler_metadata=scheduler_metadata,
        )
        self._release_tool_resource_locks(
            run_id=run_id,
            session_id=session_id,
            acquired_locks=acquired_locks,
        )
        tool_call_payload = _tool_call_payload(tool_call)
        if _tool_call_failed_with_observation(tool_call_payload):
            self._append_tool_call_failed_event(
                run_id=run_id,
                session_id=session_id,
                tool_name=tool_name,
                tool_call_payload=tool_call_payload,
                tool_call_id=int(tool_call["id"]),
                scheduler_metadata=scheduler_metadata,
            )
            if failed_observation_mode == "replan":
                self._append_failed_observation_forwarded_for_replan(
                    run_id=run_id,
                    session_id=session_id,
                    tool_name=tool_name,
                    tool_call=tool_call_payload,
                    phase="tool_failed_observation_replan",
                )
                return tool_call_payload
            return self._recover_or_finalize_failed_tool_observation(
                run_id=run_id,
                session_id=session_id,
                tool_name=tool_name,
                tool_call=tool_call_payload,
                original_payload=payload,
                approval_mode=approval_mode,
            )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="tool.call_completed",
            visible_title="工具完成",
            visible_summary=f"{_tool_label(tool_name)} 已完成。",
            payload={"toolName": tool_name, "status": tool_result.status, "scheduler": scheduler_metadata},
            tool_call_id=int(tool_call["id"]),
            correlation_ids={"scheduler": scheduler_metadata},
        )
        completed_step = self._mark_plan_step_completed(run_id, tool_name)
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="plan.step_completed",
            visible_title="计划步骤完成",
            visible_summary=f"{_tool_label(tool_name)} 已完成。",
            payload={"toolName": tool_name, "step": completed_step},
        )
        self._append_task_updated(
            run_id=run_id,
            session_id=session_id,
            phase="tool_observation",
            current_tool=tool_name,
        )
        return tool_call_payload

    def _dispatch_tool(
        self,
        *,
        run_id: int = 0,
        session_id: int,
        message: str,
        tool_name: str,
        payload: dict[str, Any],
        sandbox_runtime: SessionSandboxRuntime | None = None,
    ) -> dict[str, Any]:
        sandbox_runtime = sandbox_runtime or SessionSandboxRuntime.from_context(
            self._session_context(session_id),
            session_id=session_id,
            run_id=0,
        )
        dispatch_payload = payload | {"message": str(payload.get("message") or message)}
        if tool_name == "echo_context":
            dispatch_payload = dispatch_payload | {"context": {"sessionId": session_id}}
        dispatch_payload = dispatch_payload | {
            "_sandbox": sandbox_runtime.execution_context(env=dict(os.environ)),
            "_skillRuntime": self._skill_runtime,
            "_aiAssistantRuntime": {"sessionId": session_id, "runId": run_id},
        }
        runner_result = self._tool_runner.run(
            tool_name,
            dispatch_payload,
            idempotency_key=_tool_idempotency_key(tool_name, payload),
        )
        runner_result = _redacted_tool_run_result(runner_result, sandbox_runtime)
        return {
            "tool_result": runner_result.tool_result,
            "duration_ms": runner_result.duration_ms,
            "runner_result": runner_result,
        }

    def _append_tool_runtime_events(
        self,
        *,
        run_id: int,
        session_id: int,
        tool_name: str,
        dispatch_result: dict[str, Any],
        tool_call_id: int,
        scheduler_metadata: dict[str, Any] | None = None,
        approval_resumed: bool = False,
    ) -> None:
        runner_result = dispatch_result.get("runner_result")
        if not isinstance(runner_result, ToolRunResult):
            return
        correlation_ids = {"scheduler": scheduler_metadata} if scheduler_metadata else None
        for event in runner_result.events:
            event_type = str(event.get("type") or "")
            if event_type not in {
                "tool.retry_scheduled",
                "tool.fallback_used",
                "tool.circuit_open",
                "tool.error_observation",
                "tool.idempotency_replayed",
                "tool.idempotency_uncertain",
            }:
                continue
            payload = {
                **dict(event.get("payload") or {}),
                "toolName": tool_name,
                "toolRuntime": {
                    "idempotencyKey": runner_result.idempotency_key,
                    "attempts": runner_result.attempts,
                    "span": runner_result.span,
                    "budget": runner_result.budget,
                },
            }
            if scheduler_metadata:
                payload["scheduler"] = scheduler_metadata
            if approval_resumed:
                payload["approvalResumed"] = True
            self._repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type=event_type,
                visible_title=_tool_runtime_event_title(event_type),
                visible_summary=_tool_runtime_event_summary(event_type, payload),
                payload=payload,
                level="warning"
                if event_type in {"tool.circuit_open", "tool.error_observation", "tool.idempotency_uncertain"}
                else "info",
                tool_call_id=tool_call_id,
                correlation_ids=correlation_ids,
            )
        skill_audit_events = runner_result.tool_result.output.get("_auditEvents")
        if isinstance(skill_audit_events, list):
            for event in skill_audit_events:
                if not isinstance(event, dict):
                    continue
                event_type = str(event.get("type") or "")
                if event_type not in {"skill.load_started", "skill.loaded", "skill.resource_read", "skill.script_invoked"}:
                    continue
                payload = {
                    **dict(event.get("payload") or {}),
                    "toolName": tool_name,
                    "toolRuntime": {
                        "idempotencyKey": runner_result.idempotency_key,
                        "attempts": runner_result.attempts,
                        "span": runner_result.span,
                        "budget": runner_result.budget,
                    },
                }
                if scheduler_metadata:
                    payload["scheduler"] = scheduler_metadata
                if approval_resumed:
                    payload["approvalResumed"] = True
                self._repository.append_event(
                    run_id=run_id,
                    session_id=session_id,
                    event_type=event_type,
                    visible_title=_skill_audit_event_title(event_type),
                    visible_summary=_skill_audit_event_summary(event_type, payload),
                    payload=payload,
                    level="info",
                    tool_call_id=tool_call_id,
                    correlation_ids=correlation_ids,
                )
        observation = runner_result.tool_result.output.get("observation")
        if isinstance(observation, dict):
            self._repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type="plan.revised",
                visible_title="计划已修订",
                visible_summary="工具失败已转为结构化 observation，可用于重试、换参、换工具或降级。",
                payload={
                    "planId": _plan_payload_from_run(self._repository.get_run(run_id) or {}).get("id"),
                    "reason": "tool_error_observation",
                    "toolName": tool_name,
                    "observation": observation,
                },
                level="warning",
                tool_call_id=tool_call_id,
                correlation_ids=correlation_ids,
            )

    def _persist_plan_state(self, run_id: int, plan: dict[str, Any]) -> dict[str, Any]:
        run = self._repository.get_run(run_id)
        if run is None:
            raise KeyError(f"AI Assistant run not found: {run_id}")
        input_payload = dict(run.get("input_payload") or {})
        input_payload["plan"] = plan
        input_payload["planningStrategy"] = plan.get("planningStrategy") or input_payload.get("planningStrategy")
        return self._repository.update_run_input_payload(run_id, input_payload)

    def _mark_plan_step_started(self, run_id: int, tool_name: str | None) -> dict[str, Any]:
        plan = mark_plan_step_started(_plan_payload_from_run(self._repository.get_run(run_id) or {}), tool_name)
        self._persist_plan_state(run_id, plan)
        return dict(plan.get("currentStep") or {})

    def _mark_plan_step_completed(
        self,
        run_id: int,
        tool_name: str | None,
        final_result: str = "",
    ) -> dict[str, Any]:
        plan = mark_plan_step_completed(
            _plan_payload_from_run(self._repository.get_run(run_id) or {}),
            tool_name,
            final_result=final_result,
        )
        self._persist_plan_state(run_id, plan)
        return dict(plan.get("currentStep") or {})

    def _focus_plan_step(self, run_id: int, tool_name: str | None) -> dict[str, Any]:
        plan = _plan_payload_from_run(self._repository.get_run(run_id) or {})
        steps = [dict(step) for step in plan.get("steps") or [] if isinstance(step, dict)]
        for step in steps:
            if step.get("toolName") == tool_name:
                focused = {
                    **plan,
                    "steps": steps,
                    "currentStep": step,
                    "recognizedNeeds": list(plan.get("recognizedNeeds") or []),
                }
                self._persist_plan_state(run_id, focused)
                return focused
        return plan

    def _append_task_updated(
        self,
        *,
        run_id: int,
        session_id: int,
        phase: str,
        plan: dict[str, Any] | None = None,
        current_tool: str | None = None,
    ) -> None:
        current_plan = plan or _plan_payload_from_run(self._repository.get_run(run_id) or {})
        planned_tools = [str(tool_name) for tool_name in current_plan.get("plannedTools") or [] if tool_name]
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="task.updated",
            visible_title="任务更新",
            visible_summary="任务面板已同步当前计划进度。",
            payload={
                "planId": current_plan.get("id"),
                "planningStrategy": current_plan.get("planningStrategy"),
                "phase": phase,
                "currentTool": current_tool,
                "currentStep": current_plan.get("currentStep"),
                "plannedTools": planned_tools,
                "toolNames": planned_tools,
                "recognizedNeeds": current_plan.get("recognizedNeeds") or [],
                "steps": current_plan.get("steps") or [],
                "planStatus": current_plan.get("status"),
                "finalResult": current_plan.get("finalResult") or "",
            },
        )

    def _mark_plan_blocked(self, run_id: int, session_id: int, reason: str, status: str = "WAITING") -> dict[str, Any]:
        plan = mark_plan_blocked(_plan_payload_from_run(self._repository.get_run(run_id) or {}), reason)
        self._persist_plan_state(run_id, plan)
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="plan.blocked",
            visible_title="计划受阻",
            visible_summary=reason,
            payload={"planId": plan.get("id"), "reason": reason, "currentStep": plan.get("currentStep")},
            status=status,
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="task.blocked",
            visible_title="任务受阻",
            visible_summary=reason,
            payload={
                "planId": plan.get("id"),
                "planningStrategy": plan.get("planningStrategy"),
                "reason": reason,
                "currentStep": plan.get("currentStep"),
            },
            status=status,
        )
        return plan

    def _build_memory_context_snapshot(self, *, session_id: int, run_id: int, message: str) -> dict[str, Any]:
        session = self._repository.get_session(session_id) or {}
        session_context = dict(session.get("context_json") or {})
        workspace_root = Path(os.environ.get("HIFY_WORKSPACE_ROOT") or os.getcwd())
        workspace_start = _workspace_start_path_from_context(session_context, workspace_root)
        instruction_memory = load_instruction_memory(root_path=workspace_root, start_path=workspace_start)
        memory = memory_payload_from_context(session_context)
        active_memory = active_working_memory_items(session_context)
        session_summary = summary_from_context(session_context)
        layers = _context_budget_layers(
            instruction_layers=instruction_memory.layers,
            session_summary=session_summary,
            working_memory=active_memory,
            tool_names=[manifest.name for manifest in self._tools.list_manifests()],
            user_message=message,
        )
        context_budget = estimate_context_budget(
            layers,
            max_context_tokens=context_window_from_context(session_context),
        )
        compaction_snapshot = None
        if context_budget["droppedLayers"]:
            raw_content = "\n".join(str(layer.get("content") or "") for layer in layers)
            summary = str((session_summary or {}).get("content") or message)
            compaction_snapshot = build_compaction_snapshot(
                raw_content=raw_content,
                summary=summary,
                source_message_ids=list((session_summary or {}).get("sourceMessageIds") or []),
                source_event_ids=list((session_summary or {}).get("sourceEventIds") or []),
                algorithm="deterministic-context-budget-v1",
            )
            context_budget["compactionSnapshot"] = compaction_snapshot
        memory["instructionMemory"] = [
            {
                "name": layer["name"],
                "path": layer["path"],
                "hash": layer["hash"],
                "tokenEstimate": layer["tokenEstimate"],
            }
            for layer in instruction_memory.layers
        ]
        return {
            "memory": memory,
            "contextBudget": context_budget,
            "compactionSnapshot": compaction_snapshot,
        }

    def _append_context_budget_events(
        self,
        *,
        run_id: int,
        session_id: int,
        context_state: dict[str, Any],
    ) -> None:
        context_budget = context_state["contextBudget"]
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="context.budget_estimated",
            visible_title="上下文预算已估算",
            visible_summary=_context_budget_summary(context_budget),
            payload={"contextBudget": context_budget},
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="context.layer_selected",
            visible_title="上下文层已选择",
            visible_summary="已选择本轮可进入 prompt 的上下文层。",
            payload={"layers": context_budget["selectedLayers"]},
        )
        if context_budget["droppedLayers"]:
            compaction_snapshot = context_state.get("compactionSnapshot") or {}
            self._repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type="context.compaction_started",
                visible_title="上下文压缩开始",
                visible_summary="上下文超过预算，开始压缩或丢弃低优先级层。",
                payload={"usage": context_budget["usage"], "dropReasons": context_budget["dropReasons"]},
            )
            self._repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type="context.layer_dropped",
                visible_title="上下文层已丢弃",
                visible_summary="低优先级上下文层已被排除在本轮 prompt 外。",
                payload={"layers": context_budget["droppedLayers"], "dropReasons": context_budget["dropReasons"]},
            )
            self._repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type="context.compaction_completed",
                visible_title="上下文压缩完成",
                visible_summary=_compaction_summary(compaction_snapshot),
                payload={"compactionSnapshot": compaction_snapshot},
            )

    def _append_persisted_context_budget_events(
        self,
        *,
        run_id: int,
        session_id: int,
        run: dict[str, Any],
    ) -> None:
        input_payload = dict(run.get("input_payload") or {})
        context_budget = input_payload.get("contextBudget")
        if not isinstance(context_budget, dict):
            return
        self._append_context_budget_events(
            run_id=run_id,
            session_id=session_id,
            context_state={
                "contextBudget": context_budget,
                "compactionSnapshot": input_payload.get("compactionSnapshot"),
            },
        )

    def _update_session_summary_after_run(
        self,
        *,
        session_id: int,
        run_id: int,
        user_message: str,
        final_answer: str,
    ) -> None:
        session = self._repository.get_session(session_id)
        if session is None:
            return
        context = dict(session.get("context_json") or {})
        messages = self._repository.list_run_messages(run_id)
        events = self._repository.list_run_events(run_id)
        summary = _deterministic_session_summary(user_message=user_message, final_answer=final_answer)
        updated = upsert_session_summary(
            context,
            content=summary,
            source_message_ids=[int(message["id"]) for message in messages],
            source_event_ids=[int(event["id"]) for event in events],
            algorithm="deterministic-session-summary-v1",
            token_estimate=estimate_memory_tokens(summary),
        )
        self._repository.update_session_context(session_id, updated)

    def _session_context(self, session_id: int) -> dict[str, Any]:
        session = self._repository.get_session(session_id) or {}
        context = session.get("context_json")
        return dict(context) if isinstance(context, dict) else {}

    def _canonicalize_tool_payload(
        self,
        *,
        session_id: int,
        run_id: int,
        tool_name: str,
        payload: dict[str, Any],
    ) -> None:
        if tool_name not in {
            "read_workspace_file",
            "list_workspace_files",
            "search_workspace_files",
            "edit_workspace_file",
            "write_workspace_file",
            "apply_workspace_patch",
            "propose_agents_update",
        }:
            return
        raw_path = payload.get("path")
        if raw_path in (None, ""):
            return
        runtime = SessionSandboxRuntime.from_context(
            self._session_context(session_id),
            session_id=session_id,
            run_id=run_id,
        )
        workspace_root = runtime.config.workspace_root.resolve()
        candidate = (workspace_root / str(raw_path)).resolve()
        try:
            relative = candidate.relative_to(workspace_root)
        except ValueError:
            return
        payload["path"] = relative.as_posix() if relative.as_posix() else "."

    def _evaluate_tool_security(
        self,
        *,
        run_id: int,
        session_id: int,
        approval_mode: str,
        tool_name: str,
        payload: dict[str, Any],
        pending_tool_calls_after_approval: list[dict[str, Any]] | None = None,
    ) -> tuple[ToolManifest, HarnessTurnResult | None, SessionSandboxRuntime]:
        self._canonicalize_tool_payload(session_id=session_id, run_id=run_id, tool_name=tool_name, payload=payload)
        manifest = self._tools.get_manifest(tool_name)
        approval_mode_value = ApprovalMode(approval_mode)
        permission = self._evaluate_permission(
            run_id=run_id,
            session_id=session_id,
            approval_mode=approval_mode_value,
            tool_name=tool_name,
            manifest=manifest,
            payload=payload,
        )
        sandbox_decision, sandbox_runtime = self._evaluate_sandbox(
            run_id=run_id,
            session_id=session_id,
            tool_name=tool_name,
            payload=payload,
        )
        if sandbox_decision.verdict == SandboxVerdict.DENY:
            return manifest, self._complete_sandbox_denied(
                run_id=run_id,
                session_id=session_id,
                sandbox_decision=sandbox_decision,
            ), sandbox_runtime
        if permission == PermissionDecision.DENY:
            return manifest, self._complete_permission_denied(run_id=run_id, session_id=session_id), sandbox_runtime
        if permission == PermissionDecision.REQUIRE_APPROVAL:
            return manifest, self._complete_approval_required(
                run_id=run_id,
                session_id=session_id,
                tool_name=tool_name,
                manifest=manifest,
                payload=payload,
                pending_tool_calls_after_approval=pending_tool_calls_after_approval,
            ), sandbox_runtime
        return manifest, None, sandbox_runtime

    def _evaluate_permission(
        self,
        *,
        run_id: int,
        session_id: int,
        approval_mode: ApprovalMode,
        tool_name: str,
        manifest: ToolManifest,
        payload: dict[str, Any],
    ) -> PermissionDecision:
        context = self._session_context(session_id)
        if isinstance(context.get("aiAssistantPolicy"), dict):
            evaluation = SessionPermissionPolicy.from_context(context).evaluate(
                run_id=run_id,
                session_id=session_id,
                tool_name=tool_name,
                manifest=manifest,
                tool_input=payload,
                approval_mode=approval_mode,
                current_budget=_current_budget_from_context(context),
            )
            self._append_runtime_event(run_id=run_id, session_id=session_id, event=evaluation.event)
            return evaluation.decision
        decision = self._approval_policy.decide(approval_mode=approval_mode, risk_level=manifest.risk_level)
        self._append_runtime_event(
            run_id=run_id,
            session_id=session_id,
            event={
                "type": "permission.evaluated",
                "payload": {
                    "sessionId": session_id,
                    "runId": run_id,
                    "toolName": tool_name,
                    "riskLevel": manifest.risk_level.value,
                    "approvalMode": approval_mode.value,
                    "decision": _permission_decision_value(decision),
                    "matchedRuleId": "legacy",
                    "reason": "legacy approval policy",
                },
            },
        )
        return decision

    def _evaluate_sandbox(
        self,
        *,
        run_id: int,
        session_id: int,
        tool_name: str,
        payload: dict[str, Any],
    ) -> tuple[Any, SessionSandboxRuntime]:
        context = self._session_context(session_id)
        runtime = SessionSandboxRuntime.from_context(context, session_id=session_id, run_id=run_id)
        runtime_decision = runtime.evaluate(
            run_id=run_id,
            session_id=session_id,
            tool_name=tool_name,
            tool_input=payload,
        )
        self._append_runtime_event(run_id=run_id, session_id=session_id, event=runtime_decision.event)
        sandbox_decision = runtime.to_legacy_decision(runtime_decision)
        if sandbox_decision.verdict == SandboxVerdict.DENY:
            return sandbox_decision, runtime
        legacy_decision = self._sandbox_policy.evaluate(tool_name, payload)
        if legacy_decision.verdict == SandboxVerdict.DENY:
            return legacy_decision, runtime
        return sandbox_decision, runtime

    def _complete_sandbox_denied(
        self,
        *,
        run_id: int,
        session_id: int,
        sandbox_decision: Any,
    ) -> HarnessTurnResult:
        plan = self._mark_plan_blocked(run_id, session_id, sandbox_decision.reason, status="DENIED")
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="sandbox.denied",
            visible_title="沙箱拒绝",
            visible_summary=sandbox_decision.reason,
            payload=sandbox_decision.evidence,
            status="DENIED",
        )
        response_payload = {
            "finalAnswer": "沙箱已拒绝该工具请求。",
            "toolCalls": [],
            "approvalRequired": False,
            "sandboxDenied": True,
            "plan": plan,
        }
        denied = self._repository.complete_run(run_id, response_payload, status="DENIED")
        return HarnessTurnResult(
            run=denied,
            replayed=False,
            final_answer=str(response_payload["finalAnswer"]),
            tool_calls=[],
            sandbox_denied=True,
        )

    def _complete_permission_denied(self, *, run_id: int, session_id: int) -> HarnessTurnResult:
        plan = self._mark_plan_blocked(run_id, session_id, "审批策略已拒绝该工具请求。", status="DENIED")
        response_payload = {
            "finalAnswer": "审批策略已拒绝该工具请求。",
            "toolCalls": [],
            "approvalRequired": False,
            "sandboxDenied": False,
            "plan": plan,
        }
        denied = self._repository.complete_run(run_id, response_payload, status="DENIED")
        return HarnessTurnResult(
            run=denied,
            replayed=False,
            final_answer=str(response_payload["finalAnswer"]),
            tool_calls=[],
        )

    def _complete_approval_required(
        self,
        *,
        run_id: int,
        session_id: int,
        tool_name: str,
        manifest: ToolManifest,
        payload: dict[str, Any],
        pending_tool_calls_after_approval: list[dict[str, Any]] | None = None,
    ) -> HarnessTurnResult:
        plan = self._mark_plan_blocked(run_id, session_id, f"{_tool_label(tool_name)} 需要审批")
        approval = self._repository.create_approval(
            run_id=run_id,
            session_id=session_id,
            tool_name=tool_name,
            risk_level=manifest.risk_level.value,
            input_payload=payload,
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="approval.required",
            visible_title="需要审批",
            visible_summary=f"{_tool_label(tool_name)} 需要审批后才能执行。",
            payload={"approvalId": approval["id"], "toolName": tool_name, "riskLevel": manifest.risk_level.value},
            status="WAITING",
        )
        if manifest.risk_level.value == "BUSINESS_WRITE":
            proposed_action = self._repository.create_proposed_action(
                run_id=run_id,
                session_id=session_id,
                approval_id=int(approval["id"]),
                action_type=tool_name,
                title=f"拟执行动作：{_tool_label(tool_name)}",
                payload=payload,
            )
            self._repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type="proposed_action.created",
                visible_title="已创建拟执行动作",
                visible_summary=f"{_tool_label(tool_name)} 已转换为需要审批的拟执行动作。",
                payload={"proposedActionId": proposed_action["id"], "approvalId": approval["id"]},
            )
        response_payload = {
            "finalAnswer": "该动作需要审批后才能继续。",
            "toolCalls": [],
            "approvalRequired": True,
            "approvalId": approval["id"],
            "sandboxDenied": False,
            "pendingToolCallsAfterApproval": pending_tool_calls_after_approval or [],
            "plan": plan,
        }
        waiting = self._repository.complete_run(run_id, response_payload, status="WAITING_APPROVAL")
        return HarnessTurnResult(
            run=waiting,
            replayed=False,
            final_answer=str(response_payload["finalAnswer"]),
            tool_calls=[],
            approval_required=True,
            approval_id=int(approval["id"]),
        )

    def _append_runtime_event(self, *, run_id: int, session_id: int, event: dict[str, Any]) -> None:
        event_type = str(event.get("type") or "")
        payload = dict(event.get("payload") or {})
        denied = payload.get("decision") == "deny" or payload.get("verdict") == "deny"
        contended = event_type == "resource_lock.contended"
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type=event_type,
            visible_title=_runtime_event_title(event_type),
            visible_summary=_runtime_event_summary(event_type, payload),
            payload=payload,
            status="DENIED" if denied else "FAILED" if contended else "COMPLETED",
            level="warning" if denied or contended else "info",
        )

    def _acquire_tool_resource_locks(
        self,
        *,
        run_id: int,
        session_id: int,
        manifest: ToolManifest,
        payload: dict[str, Any],
        tool_name: str,
    ) -> tuple[list[ResourceLockAcquireResult], HarnessTurnResult | None]:
        acquired: list[ResourceLockAcquireResult] = []
        for resource_key, mode in _tool_resource_locks(
            manifest=manifest,
            payload=payload,
            session_id=session_id,
            run_id=run_id,
        ):
            result = self._resource_locks.acquire(
                resource_key=resource_key,
                mode=mode,
                owner_session_id=session_id,
                owner_run_id=run_id,
            )
            for event in result.events:
                self._append_runtime_event(run_id=run_id, session_id=session_id, event=event)
            if result.status == "CONTENDED":
                self._release_tool_resource_locks(run_id=run_id, session_id=session_id, acquired_locks=acquired)
                return acquired, self._record_resource_lock_contention(
                    run_id=run_id,
                    session_id=session_id,
                    tool_name=tool_name,
                    payload=payload,
                    lock_result=result,
                )
            acquired.append(result)
        return acquired, None

    def _release_tool_resource_locks(
        self,
        *,
        run_id: int,
        session_id: int,
        acquired_locks: list[ResourceLockAcquireResult],
    ) -> None:
        for acquired in reversed(acquired_locks):
            released = self._resource_locks.release(
                resource_key=acquired.resource_key,
                owner_session_id=session_id,
                owner_run_id=run_id,
                fencing_token=acquired.fencing_token,
            )
            if released:
                self._append_runtime_event(
                    run_id=run_id,
                    session_id=session_id,
                    event=release_event(
                        resource_key=acquired.resource_key,
                        mode=acquired.mode,
                        owner_session_id=session_id,
                        owner_run_id=run_id,
                        fencing_token=acquired.fencing_token,
                    ),
                )

    def _record_resource_lock_contention(
        self,
        *,
        run_id: int,
        session_id: int,
        tool_name: str,
        payload: dict[str, Any],
        lock_result: ResourceLockAcquireResult,
    ) -> HarnessTurnResult:
        tool_call_payload = self._record_resource_lock_contention_tool_call(
            run_id=run_id,
            session_id=session_id,
            tool_name=tool_name,
            payload=payload,
            lock_result=lock_result,
        )
        return self._finalize_failed_tool_observation(
            run_id=run_id,
            session_id=session_id,
            tool_name=tool_name,
            tool_call=tool_call_payload,
        )

    def _record_resource_lock_contention_tool_call(
        self,
        *,
        run_id: int,
        session_id: int,
        tool_name: str,
        payload: dict[str, Any],
        lock_result: ResourceLockAcquireResult,
    ) -> dict[str, Any]:
        observation = lock_result.observation
        error = dict(observation.get("error") or {})
        output_payload = {
            "status": "FAILED",
            "message": str(error.get("message") or "resource lock is contended"),
            "observation": observation,
        }
        tool_call = self._repository.record_tool_call(
            run_id=run_id,
            session_id=session_id,
            tool_name=tool_name,
            input_payload=_tool_record_input(
                payload,
                dispatch_result={},
                extra={
                    "_resourceLocks": [
                        {
                            "resourceKey": lock_result.resource_key,
                            "mode": lock_result.mode.value,
                            "status": lock_result.status,
                        }
                    ]
                },
            ),
            output_payload=output_payload,
            status="FAILED",
            duration_ms=0,
        )
        tool_call_payload = _tool_call_payload(tool_call)
        self._append_tool_call_failed_event(
            run_id=run_id,
            session_id=session_id,
            tool_name=tool_name,
            tool_call_payload=tool_call_payload,
            tool_call_id=int(tool_call["id"]),
        )
        return tool_call_payload

    def _annotate_tool_result_with_locks(
        self,
        dispatch_result: dict[str, Any],
        acquired_locks: list[ResourceLockAcquireResult],
    ) -> None:
        write_lock = next((lock for lock in acquired_locks if lock.mode == ResourceLockMode.WRITE), None)
        if write_lock is None:
            return
        tool_result = dispatch_result.get("tool_result")
        if not isinstance(tool_result, ToolResult):
            return
        dispatch_result["tool_result"] = ToolResult(
            status=tool_result.status,
            output=dict(tool_result.output)
            | {
                "lock": {
                    "mode": write_lock.mode.value,
                    "scope": "db",
                    "resource": write_lock.resource_key,
                    "fencingToken": write_lock.fencing_token,
                    "leaseExpiresAt": write_lock.lease_expires_at,
                }
            },
        )

    def get_run(self, run_id: int) -> dict[str, Any] | None:
        return self._repository.get_run(run_id)

    def list_session_runs(self, session_id: int) -> list[dict[str, Any]]:
        return self._repository.list_session_runs(session_id)

    def list_run_events(self, run_id: int, after_sequence: int = 0) -> list[dict[str, Any]]:
        return self._repository.list_run_events(run_id, after_sequence=after_sequence)

    def list_run_tool_calls(self, run_id: int) -> list[dict[str, Any]]:
        return self._repository.list_run_tool_calls(run_id)

    def get_run_inspector(self, run_id: int) -> dict[str, Any] | None:
        run = self._repository.get_run(run_id)
        if run is None:
            return None
        events = self._repository.list_run_events(run_id)
        approvals = self._repository.list_run_approvals(run_id)
        pending_approvals = [row for row in approvals if row["status"] == "PENDING"]
        tool_calls = self._repository.list_run_tool_calls(run_id)
        observability = build_observability_snapshot(
            run=run,
            events=events,
            tool_calls=tool_calls,
            approvals=approvals,
        )
        input_payload = dict(run.get("input_payload") or {})
        memory = _inspector_memory_payload(
            run_input_payload=input_payload,
            session_context=dict(
                (self._repository.get_session(int(run["session_id"])) or {}).get("context_json") or {}
            ),
        )
        return {
            "run": _run_payload(run),
            "plan": _plan_payload_from_run(run),
            "activeTasks": [_task_payload(run, events, approvals)],
            "toolCalls": [_tool_call_payload(row) for row in tool_calls],
            "approvalQueue": [_approval_payload(row) for row in pending_approvals],
            "approvalHistory": [_approval_payload(row) for row in approvals],
            "recentErrors": [_event_timeline_payload(row) for row in _recent_error_events(events)],
            "eventTimeline": [_event_timeline_payload(row) for row in events],
            "usage": observability["usage"],
            "observability": observability,
            "memory": memory,
            "contextBudget": dict(input_payload.get("contextBudget") or _context_budget_from_events(events)),
        }

    def get_run_audit_export(self, run_id: int) -> dict[str, Any] | None:
        run = self._repository.get_run(run_id)
        if run is None:
            return None
        events = self._repository.list_run_events(run_id)
        tool_calls = self._repository.list_run_tool_calls(run_id)
        approvals = self._repository.list_run_approvals(run_id)
        return build_trace_audit_export(
            run=run,
            events=events,
            tool_calls=tool_calls,
            approvals=approvals,
        )

    def list_tool_manifests(self) -> list[dict[str, Any]]:
        return [_manifest_payload(manifest) for manifest in self._tools.list_manifests()]

    def list_pending_approvals(self) -> list[dict[str, Any]]:
        return [_approval_payload(row) for row in self._repository.list_pending_approvals()]

    def approve(self, approval_id: int, actor_id: str) -> dict[str, Any]:
        current = self._repository.get_approval(approval_id)
        if current is None:
            raise KeyError(f"AI Assistant approval not found: {approval_id}")
        if current["status"] != "PENDING":
            raise RunControlConflict(f"Approval {approval_id} is not pending")
        run = self._repository.get_run(int(current["run_id"]))
        if run is None:
            raise KeyError(f"AI Assistant run not found: {current['run_id']}")
        if run["status"] != "WAITING_APPROVAL":
            raise RunControlConflict(f"Run {run['id']} is not waiting for approval")
        approval = self._repository.decide_approval(approval_id, "APPROVED", actor_id)
        run_id = int(approval["run_id"])
        session_id = int(approval["session_id"])
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="approval.granted",
            visible_title="审批通过",
            visible_summary=f"{actor_id} 已批准 {_tool_label(str(approval['tool_name']))}。",
            payload={"approvalId": approval_id, "actorId": actor_id},
        )
        message = str((run.get("input_payload") or {}).get("message") or "")
        tool_name = str(approval["tool_name"])
        run_response = dict(run.get("response_payload") or {})
        pending_tool_calls = _pending_tool_calls_after_approval(run_response)
        tool_call = self._execute_approved_tool(
            run_id=run_id,
            session_id=session_id,
            message=message,
            tool_name=tool_name,
            payload=dict(approval.get("input_payload") or {}),
        )
        if _tool_call_failed_with_observation(tool_call):
            current_run = self._repository.get_run(run_id) or {}
            if current_run.get("status") != "FAILED":
                self._finalize_failed_approved_tool(
                    run_id=run_id,
                    session_id=session_id,
                    approval_id=approval_id,
                    tool_name=tool_name,
                    tool_call=tool_call,
                )
            return _approval_payload(approval)
        if pending_tool_calls:
            execution = self._execute_scheduled_tool_calls(
                session_id=session_id,
                run_id=run_id,
                message=message,
                approval_mode=str(
                    (run.get("input_payload") or {}).get("approvalMode") or ApprovalMode.SMART_APPROVAL.value
                ),
                tool_calls=pending_tool_calls,
            )
            if execution.terminal_result is not None:
                return _approval_payload(approval)
        tool_calls = [_tool_call_payload(row) for row in self._repository.list_run_tool_calls(run_id)]
        final_answer = (
            _tool_execution_answer(tool_calls)
            if pending_tool_calls
            else f"已执行审批通过的工具：{_tool_label(tool_name)}。"
        )
        output_hint = str(tool_call.get("output", {}).get("echo") or tool_call.get("output", {}).get("path") or "")
        if output_hint and not pending_tool_calls:
            final_answer = f"{final_answer}结果：{output_hint}"
        plan = set_plan_final_result(_plan_payload_from_run(self._repository.get_run(run_id) or {}), final_answer)
        self._persist_plan_state(run_id, plan)
        self._repository.append_message(session_id, "assistant", final_answer, run_id=run_id)
        response_payload = {
            "finalAnswer": final_answer,
            "toolCalls": tool_calls,
            "approvalRequired": False,
            "approvalId": approval_id,
            "sandboxDenied": False,
            "pendingToolCallsAfterApproval": [],
            "plan": plan,
        }
        completed = self._repository.complete_run(run_id, response_payload)
        if completed.get("status") != "COMPLETED":
            return _approval_payload(approval)
        self._append_persisted_context_budget_events(
            run_id=run_id,
            session_id=session_id,
            run=completed,
        )
        self._append_task_updated(
            run_id=run_id,
            session_id=session_id,
            phase="approval_resume_finalize",
            plan=plan,
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="task.completed",
            visible_title="任务完成",
            visible_summary="审批通过后的结构化计划已执行完成。",
            payload={"planId": plan.get("id"), "finalResult": final_answer},
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="run.completed",
            visible_title="运行完成",
            visible_summary="审批通过的工具已执行，AI 助手运行已完成。",
            payload={"finalAnswer": final_answer},
        )
        return _approval_payload(approval)

    def _finalize_failed_approved_tool(
        self,
        *,
        run_id: int,
        session_id: int,
        approval_id: int,
        tool_name: str,
        tool_call: dict[str, Any],
    ) -> None:
        self._finalize_failed_tool_observation(
            run_id=run_id,
            session_id=session_id,
            tool_name=tool_name,
            tool_call=tool_call,
            approval_id=approval_id,
            final_answer_prefix="审批通过后的工具执行失败",
            task_phase="approval_resume_failed_observation",
            run_failed_summary="审批通过后的工具失败已保留为结构化 observation。",
        )

    def _append_failed_observation_forwarded_for_replan(
        self,
        *,
        run_id: int,
        session_id: int,
        tool_name: str,
        tool_call: dict[str, Any],
        phase: str,
    ) -> None:
        observation = _observation_from_tool_call(tool_call)
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="tool.observation_forwarded",
            visible_title="工具 observation 已转交",
            visible_summary="工具失败 observation 已转交给编排器继续规划。",
            payload={"toolName": tool_name, "observation": observation},
            level="warning",
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="plan.revised",
            visible_title="计划已修订",
            visible_summary="工具 observation 已进入下一轮模型/编排输入。",
            payload={
                "planId": _plan_payload_from_run(self._repository.get_run(run_id) or {}).get("id"),
                "reason": "tool_observation_replan",
                "toolName": tool_name,
                "observation": observation,
            },
            level="warning",
        )
        self._append_task_updated(
            run_id=run_id,
            session_id=session_id,
            phase=phase,
            current_tool=tool_name,
        )

    def _recover_or_finalize_failed_tool_observation(
        self,
        *,
        run_id: int,
        session_id: int,
        tool_name: str,
        tool_call: dict[str, Any],
        original_payload: dict[str, Any],
        approval_mode: str,
        approval_id: int | None = None,
        final_answer_prefix: str = "工具执行失败",
        task_phase: str = "tool_failed_observation",
        run_failed_summary: str = "工具失败已保留为结构化 observation。",
    ) -> HarnessTurnResult:
        run = self._repository.get_run(run_id) or {}
        try:
            manifest = self._tools.get_manifest(tool_name)
            risk_level = manifest.risk_level.value
        except Exception:
            risk_level = RiskLevel.READ.value
        observation = _observation_from_tool_call(tool_call)
        decision = plan_tool_self_correction(
            tool_name=tool_name,
            tool_input=original_payload,
            observation=observation,
            ai_assistant_budget=dict((run.get("input_payload") or {}).get("aiAssistantBudget") or {}),
            previous_repair_attempts=_self_correction_attempt_count(self._repository.list_run_events(run_id)),
            risk_level=risk_level,
        )
        action = str(decision.get("action") or "terminal")
        if action in {"retry_tool", "fallback_tool"}:
            return self._execute_self_correction_tool_call(
                run_id=run_id,
                session_id=session_id,
                failed_tool_name=tool_name,
                failed_tool_call=tool_call,
                decision=decision,
                approval_mode=approval_mode,
            )
        if action == "degrade":
            return self._complete_degraded_tool_observation(
                run_id=run_id,
                session_id=session_id,
                tool_name=tool_name,
                tool_call=tool_call,
                decision=decision,
            )
        if action == "budget_exhausted":
            self._append_self_correction_event(
                run_id=run_id,
                session_id=session_id,
                event_type="tool.self_correction_exhausted",
                tool_name=tool_name,
                decision=decision,
                observation=observation,
                level="warning",
            )
        else:
            self._append_self_correction_event(
                run_id=run_id,
                session_id=session_id,
                event_type="tool.self_correction_terminal",
                tool_name=tool_name,
                decision=decision,
                observation=observation,
                level="warning",
            )
        return self._finalize_failed_tool_observation(
            run_id=run_id,
            session_id=session_id,
            tool_name=tool_name,
            tool_call=tool_call,
            approval_id=approval_id,
            final_answer_prefix=final_answer_prefix,
            task_phase=task_phase,
            run_failed_summary=run_failed_summary,
        )

    def _execute_self_correction_tool_call(
        self,
        *,
        run_id: int,
        session_id: int,
        failed_tool_name: str,
        failed_tool_call: dict[str, Any],
        decision: dict[str, Any],
        approval_mode: str,
    ) -> HarnessTurnResult:
        tool_name = str(decision.get("toolName") or failed_tool_name)
        payload = dict(decision.get("toolInput") or {})
        observation = _observation_from_tool_call(failed_tool_call)
        self._append_self_correction_event(
            run_id=run_id,
            session_id=session_id,
            event_type="tool.self_correction_started",
            tool_name=failed_tool_name,
            decision=decision,
            observation=observation,
        )
        if decision.get("action") == "fallback_tool":
            self._append_self_correction_event(
                run_id=run_id,
                session_id=session_id,
                event_type="tool.self_correction_fallback_selected",
                tool_name=tool_name,
                decision=decision,
                observation=observation,
            )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="plan.revised",
            visible_title="计划已修订",
            visible_summary="工具失败 observation 已触发自动修复计划。",
            payload={
                "planId": _plan_payload_from_run(self._repository.get_run(run_id) or {}).get("id"),
                "reason": "tool_observation_self_correction",
                "toolName": failed_tool_name,
                "repairToolName": tool_name,
                "decision": decision,
                "observation": observation,
            },
            level="warning",
        )
        self._append_task_updated(
            run_id=run_id,
            session_id=session_id,
            phase="tool_self_correction",
            current_tool=tool_name,
        )
        manifest, gate_result, sandbox_runtime = self._evaluate_tool_security(
            run_id=run_id,
            session_id=session_id,
            approval_mode=approval_mode,
            tool_name=tool_name,
            payload=payload,
        )
        if gate_result is not None:
            self._append_self_correction_event(
                run_id=run_id,
                session_id=session_id,
                event_type="tool.self_correction_terminal",
                tool_name=tool_name,
                decision=decision | {"reason": "repair_tool_security_gate"},
                observation=observation,
                level="warning",
            )
            return self._finalize_failed_tool_observation(
                run_id=run_id,
                session_id=session_id,
                tool_name=failed_tool_name,
                tool_call=failed_tool_call,
            )
        acquired_locks, lock_result = self._acquire_tool_resource_locks(
            run_id=run_id,
            session_id=session_id,
            manifest=manifest,
            payload=payload,
            tool_name=tool_name,
        )
        if lock_result is not None:
            self._append_self_correction_event(
                run_id=run_id,
                session_id=session_id,
                event_type="tool.self_correction_terminal",
                tool_name=tool_name,
                decision=decision | {"reason": "repair_tool_resource_lock"},
                observation=observation,
                level="warning",
            )
            return self._finalize_failed_tool_observation(
                run_id=run_id,
                session_id=session_id,
                tool_name=failed_tool_name,
                tool_call=failed_tool_call,
            )
        started_step = self._mark_plan_step_started(run_id, tool_name)
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="plan.step_started",
            visible_title="计划步骤开始",
            visible_summary=f"{_tool_label(tool_name)} 修复步骤已开始。",
            payload={"toolName": tool_name, "step": started_step, "selfCorrection": True},
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="tool.call_started",
            visible_title="工具开始",
            visible_summary=f"{_tool_label(tool_name)} 自纠错调用已开始执行。",
            payload={"toolName": tool_name, "input": payload, "selfCorrection": True},
        )
        dispatch_result = self._dispatch_tool(
            run_id=run_id,
            session_id=session_id,
            message="",
            tool_name=tool_name,
            payload=payload,
            sandbox_runtime=sandbox_runtime,
        )
        self._annotate_tool_result_with_locks(dispatch_result, acquired_locks)
        tool_result = dispatch_result["tool_result"]
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="tool.call_output",
            visible_title="工具输出",
            visible_summary=_tool_result_visible_summary(tool_result.output),
            payload={"toolName": tool_name, "output": tool_result.output, "selfCorrection": True},
        )
        tool_call = self._repository.record_tool_call(
            run_id=run_id,
            session_id=session_id,
            tool_name=tool_name,
            input_payload=_tool_record_input(payload, dispatch_result=dispatch_result, extra={"_selfCorrection": decision}),
            output_payload=tool_result.output,
            status=tool_result.status,
            duration_ms=int(dispatch_result["duration_ms"]),
        )
        self._append_tool_runtime_events(
            run_id=run_id,
            session_id=session_id,
            tool_name=tool_name,
            dispatch_result=dispatch_result,
            tool_call_id=int(tool_call["id"]),
        )
        self._release_tool_resource_locks(run_id=run_id, session_id=session_id, acquired_locks=acquired_locks)
        repaired_tool_call = _tool_call_payload(tool_call)
        if _tool_call_failed_with_observation(repaired_tool_call):
            self._append_tool_call_failed_event(
                run_id=run_id,
                session_id=session_id,
                tool_name=tool_name,
                tool_call_payload=repaired_tool_call,
                tool_call_id=int(tool_call["id"]),
            )
            self._append_self_correction_event(
                run_id=run_id,
                session_id=session_id,
                event_type="tool.self_correction_exhausted",
                tool_name=tool_name,
                decision=decision | {"reason": "repair_attempt_failed"},
                observation=_observation_from_tool_call(repaired_tool_call),
                level="warning",
            )
            return self._finalize_failed_tool_observation(
                run_id=run_id,
                session_id=session_id,
                tool_name=tool_name,
                tool_call=repaired_tool_call,
            )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="tool.call_completed",
            visible_title="工具完成",
            visible_summary=f"{_tool_label(tool_name)} 自纠错调用已完成。",
            payload={"toolName": tool_name, "status": tool_result.status, "selfCorrection": True},
            tool_call_id=int(tool_call["id"]),
        )
        completed_step = self._mark_plan_step_completed(run_id, tool_name)
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="plan.step_completed",
            visible_title="计划步骤完成",
            visible_summary=f"{_tool_label(tool_name)} 修复步骤已完成。",
            payload={"toolName": tool_name, "step": completed_step, "selfCorrection": True},
        )
        return self._complete_self_corrected_tool_run(
            run_id=run_id,
            session_id=session_id,
            tool_name=tool_name,
            decision=decision,
        )

    def _complete_self_corrected_tool_run(
        self,
        *,
        run_id: int,
        session_id: int,
        tool_name: str,
        decision: dict[str, Any],
    ) -> HarnessTurnResult:
        tool_calls = [_tool_call_payload(row) for row in self._repository.list_run_tool_calls(run_id)]
        final_answer = _tool_execution_answer(tool_calls)
        self._append_self_correction_event(
            run_id=run_id,
            session_id=session_id,
            event_type="tool.self_correction_completed",
            tool_name=tool_name,
            decision=decision,
            observation=_observation_from_tool_call(tool_calls[0]) if tool_calls else {},
        )
        self._append_model_output_stream(
            run_id=run_id,
            session_id=session_id,
            model="deterministic",
            text=final_answer,
            phase="final_answer",
            source="harness_self_correction",
        )
        self._repository.append_message(session_id, "assistant", final_answer, run_id=run_id)
        plan = set_plan_final_result(_plan_payload_from_run(self._repository.get_run(run_id) or {}), final_answer)
        self._persist_plan_state(run_id, plan)
        completed = self._repository.complete_run(
            run_id,
            {
                "finalAnswer": final_answer,
                "toolCalls": tool_calls,
                "approvalRequired": False,
                "sandboxDenied": False,
                "plan": plan,
            },
        )
        self._append_task_updated(
            run_id=run_id,
            session_id=session_id,
            phase="tool_self_correction_completed",
            plan=plan,
            current_tool=tool_name,
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="task.completed",
            visible_title="任务完成",
            visible_summary="工具失败已自纠错，结构化计划已执行完成。",
            payload={"planId": plan.get("id"), "finalResult": final_answer},
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="run.completed",
            visible_title="运行完成",
            visible_summary="AI 助手已通过工具 observation 自纠错完成运行。",
            payload={"finalAnswer": final_answer},
        )
        self._update_session_summary_after_run(
            session_id=session_id,
            run_id=run_id,
            user_message=str(((completed or {}).get("input_payload") or {}).get("message") or ""),
            final_answer=final_answer,
        )
        return HarnessTurnResult(
            run=completed,
            replayed=False,
            final_answer=final_answer,
            tool_calls=tool_calls,
        )

    def _complete_degraded_tool_observation(
        self,
        *,
        run_id: int,
        session_id: int,
        tool_name: str,
        tool_call: dict[str, Any],
        decision: dict[str, Any],
    ) -> HarnessTurnResult:
        tool_calls = [_tool_call_payload(row) for row in self._repository.list_run_tool_calls(run_id)]
        reason = _tool_failure_reason(tool_call)
        final_answer = str(
            decision.get("finalAnswer")
            or f"工具 {_tool_label(tool_name)} 暂时不可用，已根据 observation 降级完成：{reason}"
        )
        self._append_self_correction_event(
            run_id=run_id,
            session_id=session_id,
            event_type="tool.self_correction_degraded",
            tool_name=tool_name,
            decision=decision,
            observation=_observation_from_tool_call(tool_call),
        )
        completed_step = self._mark_plan_step_completed(run_id, tool_name, final_answer)
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="plan.step_completed",
            visible_title="计划步骤完成",
            visible_summary=f"{_tool_label(tool_name)} 已通过降级策略完成。",
            payload={"toolName": tool_name, "step": completed_step, "selfCorrection": True, "degraded": True},
        )
        self._append_model_output_stream(
            run_id=run_id,
            session_id=session_id,
            model="deterministic",
            text=final_answer,
            phase="final_answer",
            source="harness_self_correction_degrade",
        )
        self._repository.append_message(session_id, "assistant", final_answer, run_id=run_id)
        plan = set_plan_final_result(_plan_payload_from_run(self._repository.get_run(run_id) or {}), final_answer)
        self._persist_plan_state(run_id, plan)
        completed = self._repository.complete_run(
            run_id,
            {
                "finalAnswer": final_answer,
                "toolCalls": tool_calls,
                "approvalRequired": False,
                "sandboxDenied": False,
                "plan": plan,
            },
        )
        self._append_task_updated(
            run_id=run_id,
            session_id=session_id,
            phase="tool_self_correction_degraded",
            plan=plan,
            current_tool=tool_name,
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="task.completed",
            visible_title="任务完成",
            visible_summary="工具失败已通过降级策略完成。",
            payload={"planId": plan.get("id"), "finalResult": final_answer},
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="run.completed",
            visible_title="运行完成",
            visible_summary="AI 助手已通过工具 observation 降级完成运行。",
            payload={"finalAnswer": final_answer},
        )
        return HarnessTurnResult(
            run=completed,
            replayed=False,
            final_answer=final_answer,
            tool_calls=tool_calls,
        )

    def _append_self_correction_event(
        self,
        *,
        run_id: int,
        session_id: int,
        event_type: str,
        tool_name: str,
        decision: dict[str, Any],
        observation: dict[str, Any],
        level: str = "info",
    ) -> None:
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type=event_type,
            visible_title=_self_correction_event_title(event_type),
            visible_summary=_self_correction_event_summary(event_type, tool_name),
            payload={
                "toolName": tool_name,
                "decision": decision,
                "observation": observation,
                "budget": {"maxToolRepairAttempts": decision.get("maxToolRepairAttempts")},
            },
            level=level,
        )

    def _finalize_failed_tool_observation(
        self,
        *,
        run_id: int,
        session_id: int,
        tool_name: str,
        tool_call: dict[str, Any],
        approval_id: int | None = None,
        final_answer_prefix: str = "工具执行失败",
        task_phase: str = "tool_failed_observation",
        run_failed_summary: str = "工具失败已保留为结构化 observation。",
    ) -> HarnessTurnResult:
        tool_calls = [_tool_call_payload(row) for row in self._repository.list_run_tool_calls(run_id)]
        reason = _tool_failure_reason(tool_call)
        self._focus_plan_step(run_id, tool_name)
        plan = self._mark_plan_blocked(run_id, session_id, reason, status="FAILED")
        final_answer = f"{final_answer_prefix}：{reason}"
        self._repository.append_message(session_id, "assistant", final_answer, run_id=run_id)
        response_payload = {
            "finalAnswer": final_answer,
            "toolCalls": tool_calls,
            "approvalRequired": False,
            "sandboxDenied": False,
            "pendingToolCallsAfterApproval": [],
            "plan": plan,
        }
        if approval_id is not None:
            response_payload["approvalId"] = approval_id
        failed = self._repository.complete_run(run_id, response_payload, status="FAILED")
        self._append_task_updated(
            run_id=run_id,
            session_id=session_id,
            phase=task_phase,
            plan=plan,
            current_tool=tool_name,
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="run.failed",
            visible_title="运行失败",
            visible_summary=run_failed_summary,
            payload={
                "finalAnswer": final_answer,
                "toolName": tool_name,
                "observation": tool_call.get("output", {}).get("observation"),
            },
            status="FAILED",
        )
        return HarnessTurnResult(
            run=failed,
            replayed=False,
            final_answer=final_answer,
            tool_calls=tool_calls,
        )

    def _append_tool_call_failed_event(
        self,
        *,
        run_id: int,
        session_id: int,
        tool_name: str,
        tool_call_payload: dict[str, Any],
        tool_call_id: int,
        scheduler_metadata: dict[str, Any] | None = None,
        approval_resumed: bool = False,
    ) -> None:
        payload: dict[str, Any] = {
            "toolName": tool_name,
            "status": "FAILED",
            "observation": tool_call_payload.get("output", {}).get("observation"),
        }
        if scheduler_metadata:
            payload["scheduler"] = scheduler_metadata
        if approval_resumed:
            payload["approvalResumed"] = True
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="tool.call_failed",
            visible_title="工具失败",
            visible_summary=f"{_tool_label(tool_name)} 执行失败，已保留结构化 observation。",
            payload=payload,
            status="FAILED",
            tool_call_id=tool_call_id,
            correlation_ids={"scheduler": scheduler_metadata} if scheduler_metadata else None,
        )

    def deny(self, approval_id: int, actor_id: str, reason: str = "") -> dict[str, Any]:
        current = self._repository.get_approval(approval_id)
        if current is None:
            raise KeyError(f"AI Assistant approval not found: {approval_id}")
        if current["status"] != "PENDING":
            raise RunControlConflict(f"Approval {approval_id} is not pending")
        run = self._repository.get_run(int(current["run_id"]))
        if run is None:
            raise KeyError(f"AI Assistant run not found: {current['run_id']}")
        if run["status"] != "WAITING_APPROVAL":
            raise RunControlConflict(f"Run {run['id']} is not waiting for approval")
        approval = self._repository.decide_approval(approval_id, "DENIED", actor_id, reason)
        run_id = int(approval["run_id"])
        session_id = int(approval["session_id"])
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="approval.denied",
            visible_title="审批拒绝",
            visible_summary=f"{actor_id} 已拒绝 {_tool_label(str(approval['tool_name']))}。",
            payload={"approvalId": approval_id, "actorId": actor_id, "reason": reason},
            status="DENIED",
        )
        tool_calls = [_tool_call_payload(row) for row in self._repository.list_run_tool_calls(run_id)]
        final_answer = "审批已拒绝，相关工具未执行。"
        self._repository.append_message(session_id, "assistant", final_answer, run_id=run_id)
        self._repository.complete_run(
            run_id,
            {
                "finalAnswer": final_answer,
                "toolCalls": tool_calls,
                "approvalRequired": False,
                "approvalId": approval_id,
                "sandboxDenied": False,
            },
            status="DENIED",
        )
        return _approval_payload(approval)

    def _execute_approved_tool(
        self,
        *,
        run_id: int,
        session_id: int,
        message: str,
        tool_name: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        plan_before = _plan_payload_from_run(self._repository.get_run(run_id) or {})
        if plan_before.get("status") == "BLOCKED":
            self._repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type="plan.revised",
                visible_title="计划已修订",
                visible_summary="审批通过后，计划从受阻状态恢复执行。",
                payload={"planId": plan_before.get("id"), "reason": "approval_granted", "previousStatus": "BLOCKED"},
            )
        self._canonicalize_tool_payload(session_id=session_id, run_id=run_id, tool_name=tool_name, payload=payload)
        manifest = self._tools.get_manifest(tool_name)
        self._append_runtime_event(
            run_id=run_id,
            session_id=session_id,
            event={
                "type": "permission.evaluated",
                "payload": {
                    "sessionId": session_id,
                    "runId": run_id,
                    "toolName": tool_name,
                    "riskLevel": manifest.risk_level.value,
                    "approvalMode": "approved",
                    "decision": "allow",
                    "matchedRuleId": "human_approval",
                    "reason": "human approval granted",
                },
            },
        )
        sandbox_decision, sandbox_runtime = self._evaluate_sandbox(
            run_id=run_id,
            session_id=session_id,
            tool_name=tool_name,
            payload=payload,
        )
        if sandbox_decision.verdict == SandboxVerdict.DENY:
            observation = {
                "kind": "tool_error",
                "toolName": tool_name,
                "toolInput": payload,
                "attempts": 0,
                "error": {
                    "code": "SANDBOX_DENIED",
                    "message": sandbox_decision.reason,
                    "type": "sandbox_denied",
                    "retriable": False,
                },
                "retriable": False,
                "modelVisible": True,
            }
            tool_call = self._repository.record_tool_call(
                run_id=run_id,
                session_id=session_id,
                tool_name=tool_name,
                input_payload=_tool_record_input(payload, dispatch_result={}),
                output_payload={"status": "FAILED", "message": sandbox_decision.reason, "observation": observation},
                status="FAILED",
                duration_ms=0,
            )
            tool_call_payload = _tool_call_payload(tool_call)
            self._append_tool_call_failed_event(
                run_id=run_id,
                session_id=session_id,
                tool_name=tool_name,
                tool_call_payload=tool_call_payload,
                tool_call_id=int(tool_call["id"]),
                approval_resumed=True,
            )
            return tool_call_payload
        acquired_locks, lock_result = self._acquire_tool_resource_locks(
            run_id=run_id,
            session_id=session_id,
            manifest=manifest,
            payload=payload,
            tool_name=tool_name,
        )
        if lock_result is not None:
            return lock_result.tool_calls[0] if lock_result.tool_calls else {
                "id": 0,
                "toolName": tool_name,
                "input": payload,
                "output": {},
                "status": "FAILED",
                "durationMs": 0,
                "scheduler": {},
            }
        started_step = self._mark_plan_step_started(run_id, tool_name)
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="plan.step_started",
            visible_title="计划步骤开始",
            visible_summary=f"{_tool_label(tool_name)} 已开始。",
            payload={"toolName": tool_name, "step": started_step, "approvalResumed": True},
        )
        self._append_task_updated(
            run_id=run_id,
            session_id=session_id,
            phase="approval_resume_tool_execution",
            current_tool=tool_name,
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="tool.call_started",
            visible_title="工具开始",
            visible_summary=f"{_tool_label(tool_name)} 已开始执行。",
            payload={"toolName": tool_name, "input": payload, "approvalResumed": True},
        )
        dispatch_result = self._dispatch_tool(
            run_id=run_id,
            session_id=session_id,
            message=message,
            tool_name=tool_name,
            payload=payload,
            sandbox_runtime=sandbox_runtime,
        )
        self._annotate_tool_result_with_locks(dispatch_result, acquired_locks)
        tool_result = dispatch_result["tool_result"]
        duration_ms = int(dispatch_result["duration_ms"])
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="tool.call_output",
            visible_title="工具输出",
            visible_summary=_tool_result_visible_summary(tool_result.output),
            payload={"toolName": tool_name, "output": tool_result.output, "approvalResumed": True},
        )
        tool_call = self._repository.record_tool_call(
            run_id=run_id,
            session_id=session_id,
            tool_name=tool_name,
            input_payload=_tool_record_input(payload, dispatch_result=dispatch_result),
            output_payload=tool_result.output,
            status=tool_result.status,
            duration_ms=duration_ms,
        )
        self._append_tool_runtime_events(
            run_id=run_id,
            session_id=session_id,
            tool_name=tool_name,
            dispatch_result=dispatch_result,
            tool_call_id=int(tool_call["id"]),
            approval_resumed=True,
        )
        self._release_tool_resource_locks(
            run_id=run_id,
            session_id=session_id,
            acquired_locks=acquired_locks,
        )
        tool_call_payload = _tool_call_payload(tool_call)
        if _tool_call_failed_with_observation(tool_call_payload):
            self._repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type="tool.call_failed",
                visible_title="工具失败",
                visible_summary=f"{_tool_label(tool_name)} 执行失败，已保留结构化 observation。",
                payload={
                    "toolName": tool_name,
                    "status": tool_result.status,
                    "approvalResumed": True,
                    "observation": tool_result.output.get("observation"),
                },
                status="FAILED",
                tool_call_id=int(tool_call["id"]),
            )
            self._append_task_updated(
                run_id=run_id,
                session_id=session_id,
                phase="approval_resume_tool_failed_observation",
                current_tool=tool_name,
            )
            return tool_call_payload
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="tool.call_completed",
            visible_title="工具完成",
            visible_summary=f"{_tool_label(tool_name)} 已完成。",
            payload={"toolName": tool_name, "status": tool_result.status, "approvalResumed": True},
            tool_call_id=int(tool_call["id"]),
        )
        completed_step = self._mark_plan_step_completed(run_id, tool_name)
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="plan.step_completed",
            visible_title="计划步骤完成",
            visible_summary=f"{_tool_label(tool_name)} 已完成。",
            payload={"toolName": tool_name, "step": completed_step, "approvalResumed": True},
        )
        self._append_task_updated(
            run_id=run_id,
            session_id=session_id,
            phase="approval_resume_tool_observation",
            current_tool=tool_name,
        )
        return tool_call_payload


def _request_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return sha256(encoded.encode("utf-8")).hexdigest()


def plan_tool_self_correction(
    *,
    tool_name: str,
    tool_input: dict[str, Any],
    observation: dict[str, Any],
    ai_assistant_budget: dict[str, Any],
    previous_repair_attempts: int,
    risk_level: str,
) -> dict[str, Any]:
    max_attempts = _max_tool_repair_attempts(ai_assistant_budget)
    if not _observation_is_recoverable(observation):
        return {
            "action": "terminal",
            "reason": "unrecoverable_tool_observation",
            "toolName": tool_name,
            "toolInput": _public_self_correction_input(tool_input),
            "maxToolRepairAttempts": max_attempts,
        }
    if str(risk_level).upper() != RiskLevel.READ.value:
        return {
            "action": "terminal",
            "reason": "side_effect_repair_requires_human_approval",
            "toolName": tool_name,
            "toolInput": _public_self_correction_input(tool_input),
            "maxToolRepairAttempts": max_attempts,
        }
    if previous_repair_attempts >= max_attempts:
        return {
            "action": "budget_exhausted",
            "reason": "tool_repair_budget_exhausted",
            "toolName": tool_name,
            "toolInput": _public_self_correction_input(tool_input),
            "previousRepairAttempts": previous_repair_attempts,
            "maxToolRepairAttempts": max_attempts,
        }
    hints = tool_input.get("_selfCorrection")
    hints = dict(hints) if isinstance(hints, dict) else {}
    retry_input = hints.get("retryToolInput")
    if isinstance(retry_input, dict):
        return {
            "action": "retry_tool",
            "reason": "recoverable_tool_observation",
            "toolName": str(hints.get("retryToolName") or tool_name),
            "toolInput": _public_self_correction_input(retry_input),
            "previousRepairAttempts": previous_repair_attempts,
            "maxToolRepairAttempts": max_attempts,
        }
    fallback_tool_name = str(hints.get("fallbackToolName") or "")
    fallback_input = hints.get("fallbackToolInput")
    if fallback_tool_name and isinstance(fallback_input, dict):
        return {
            "action": "fallback_tool",
            "reason": "recoverable_tool_observation",
            "toolName": fallback_tool_name,
            "toolInput": _public_self_correction_input(fallback_input),
            "previousRepairAttempts": previous_repair_attempts,
            "maxToolRepairAttempts": max_attempts,
        }
    return {
        "action": "degrade",
        "reason": "recoverable_tool_observation",
        "toolName": tool_name,
        "toolInput": _public_self_correction_input(tool_input),
        "previousRepairAttempts": previous_repair_attempts,
        "maxToolRepairAttempts": max_attempts,
        "finalAnswer": hints.get("degradeAnswer") if isinstance(hints.get("degradeAnswer"), str) else "",
    }


def _max_tool_repair_attempts(ai_assistant_budget: dict[str, Any]) -> int:
    for key in ("maxToolRepairAttempts", "max_tool_repair_attempts", "maxRepairAttempts"):
        value = ai_assistant_budget.get(key)
        if value not in (None, ""):
            return max(0, int(str(value)))
    return 1


def _observation_is_recoverable(observation: dict[str, Any]) -> bool:
    if not observation:
        return False
    if observation.get("retriable") is False:
        return False
    error = observation.get("error")
    if isinstance(error, dict) and error.get("retriable") is False:
        return False
    return bool(observation.get("modelVisible", True))


def _public_self_correction_input(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if not str(key).startswith("_")}


def _observation_from_tool_call(tool_call: dict[str, Any]) -> dict[str, Any]:
    output = tool_call.get("output")
    if isinstance(output, dict) and isinstance(output.get("observation"), dict):
        return dict(output["observation"])
    return {}


def _self_correction_attempt_count(events: list[dict[str, Any]]) -> int:
    return sum(1 for event in events if event.get("type") == "tool.self_correction_started")


def _self_correction_event_title(event_type: str) -> str:
    return {
        "tool.self_correction_started": "工具自纠错开始",
        "tool.self_correction_fallback_selected": "工具降级工具已选择",
        "tool.self_correction_completed": "工具自纠错完成",
        "tool.self_correction_degraded": "工具自纠错降级",
        "tool.self_correction_exhausted": "工具自纠错预算耗尽",
        "tool.self_correction_terminal": "工具自纠错终止",
    }.get(event_type, "工具自纠错")


def _self_correction_event_summary(event_type: str, tool_name: str) -> str:
    if event_type == "tool.self_correction_started":
        return f"{_tool_label(tool_name)} 的失败 observation 已触发修复尝试。"
    if event_type == "tool.self_correction_fallback_selected":
        return f"{_tool_label(tool_name)} 已作为 fallback 工具被选择。"
    if event_type == "tool.self_correction_completed":
        return f"{_tool_label(tool_name)} 的自纠错调用已完成。"
    if event_type == "tool.self_correction_degraded":
        return f"{_tool_label(tool_name)} 不可用，已降级完成。"
    if event_type == "tool.self_correction_exhausted":
        return f"{_tool_label(tool_name)} 自纠错预算已耗尽。"
    if event_type == "tool.self_correction_terminal":
        return f"{_tool_label(tool_name)} 不满足自动自纠错条件。"
    return "工具自纠错事件已记录。"


def _redacted_tool_run_result(
    runner_result: ToolRunResult,
    sandbox_runtime: SessionSandboxRuntime,
) -> ToolRunResult:
    redacted_output, redaction_applied = sandbox_runtime.redact_payload(runner_result.tool_result.output)
    if not redaction_applied:
        return runner_result
    return ToolRunResult(
        tool_result=ToolResult(
            status=runner_result.tool_result.status,
            output=redacted_output | {"redactionApplied": True},
        ),
        duration_ms=runner_result.duration_ms,
        attempts=runner_result.attempts,
        idempotency_key=runner_result.idempotency_key,
        events=runner_result.events,
        span=runner_result.span,
        budget=runner_result.budget,
    )


def _current_budget_from_context(context: dict[str, Any]) -> int | None:
    raw_budget = context.get("aiAssistantBudget")
    if not isinstance(raw_budget, dict):
        return None
    for key in ("current", "currentBudget", "used", "usedBudget"):
        value = raw_budget.get(key)
        if value not in (None, ""):
            return int(str(value))
    return None


def _permission_decision_value(decision: PermissionDecision) -> str:
    if decision == PermissionDecision.AUTO_APPROVE:
        return "allow"
    if decision == PermissionDecision.DENY:
        return "deny"
    return "require_approval"


def _tool_resource_locks(
    *,
    manifest: ToolManifest,
    payload: dict[str, Any],
    session_id: int,
    run_id: int,
) -> list[tuple[str, ResourceLockMode]]:
    resources: dict[str, ResourceLockMode] = {}
    context = dict(payload) | {
        "session_id": session_id,
        "run_id": run_id,
        "sessionId": session_id,
        "runId": run_id,
    }
    for template in manifest.read_resources:
        resource_key = _resolve_resource_template(template, context)
        resources.setdefault(resource_key, ResourceLockMode.READ)
    for template in manifest.write_resources:
        resource_key = _resolve_resource_template(template, context)
        resources[resource_key] = ResourceLockMode.WRITE
    return [(resource_key, mode) for resource_key, mode in resources.items() if resource_key]


def _resolve_resource_template(template: str, context: dict[str, Any]) -> str:
    class _Missing(dict[str, Any]):
        def __missing__(self, key: str) -> str:
            return "{" + key + "}"

    return str(template).format_map(_Missing(context))


def _runtime_event_title(event_type: str) -> str:
    return {
        "permission.evaluated": "权限已评估",
        "sandbox.evaluated": "沙箱已评估",
        "resource_lock.acquire_requested": "资源锁申请",
        "resource_lock.acquired": "资源锁已获取",
        "resource_lock.contended": "资源锁冲突",
        "resource_lock.released": "资源锁已释放",
    }.get(event_type, event_type)


def _runtime_event_summary(event_type: str, payload: dict[str, Any]) -> str:
    if event_type == "permission.evaluated":
        return f"{payload.get('toolName')} 权限决策：{payload.get('decision')}。"
    if event_type == "sandbox.evaluated":
        return f"{payload.get('toolName')} 沙箱判定：{payload.get('verdict')}。"
    if event_type == "resource_lock.acquire_requested":
        return f"正在申请 {payload.get('resourceKey')} 的 {payload.get('mode')} 锁。"
    if event_type == "resource_lock.acquired":
        return f"已获取 {payload.get('resourceKey')} 的 {payload.get('mode')} 锁。"
    if event_type == "resource_lock.contended":
        return f"{payload.get('resourceKey')} 资源锁冲突。"
    if event_type == "resource_lock.released":
        return f"已释放 {payload.get('resourceKey')} 的 {payload.get('mode')} 锁。"
    return str(payload.get("message") or event_type)


def _context_budget_layers(
    *,
    instruction_layers: list[dict[str, Any]],
    session_summary: dict[str, Any] | None,
    working_memory: list[dict[str, Any]],
    tool_names: list[str],
    user_message: str,
) -> list[dict[str, Any]]:
    layers: list[dict[str, Any]] = [
        {"name": "base", "content": "You are Hify AI Assistant.", "source": "system"},
    ]
    for layer in instruction_layers:
        layers.append(
            {
                "name": "AGENTS.md",
                "content": str(layer.get("content") or ""),
                "source": layer.get("path"),
                "hash": layer.get("hash"),
            }
        )
    if session_summary:
        layers.append(
            {
                "name": "session_summary",
                "content": str(session_summary.get("content") or ""),
                "source": "session.context_json",
                "hash": session_summary.get("hash"),
            }
        )
    if working_memory:
        layers.append(
            {
                "name": "working_memory",
                "content": "\n".join(f"{item.get('key')}: {item.get('value')}" for item in working_memory),
                "source": "session.context_json",
            }
        )
    layers.extend(
        [
            {"name": "tools", "content": "\n".join(sorted(tool_names)), "source": "tool_registry"},
            {"name": "recent_messages", "content": user_message, "source": "current_run"},
            {"name": "user_message", "content": user_message, "source": "current_run"},
        ]
    )
    return layers


def _context_budget_summary(context_budget: dict[str, Any]) -> str:
    usage = context_budget.get("usage") or {}
    return (
        f"上下文使用 {usage.get('usedTokens', 0)} / {usage.get('maxTokens', 0)} tokens，"
        f"{usage.get('usagePercent', 0)}%。"
    )


def _compaction_summary(compaction_snapshot: dict[str, Any]) -> str:
    return (
        f"上下文压缩 {compaction_snapshot.get('rawTokens', 0)} -> "
        f"{compaction_snapshot.get('summaryTokens', 0)} tokens，"
        f"节省 {compaction_snapshot.get('savedPercent', 0)}%。"
    )


def _deterministic_session_summary(*, user_message: str, final_answer: str) -> str:
    return f"用户：{user_message}\n助手：{final_answer}"


def _context_budget_from_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    for event in reversed(events):
        if event.get("type") != "context.budget_estimated":
            continue
        payload = event.get("payload")
        if isinstance(payload, dict) and isinstance(payload.get("contextBudget"), dict):
            return dict(payload["contextBudget"])
    return {}


def _workspace_start_path_from_context(context: dict[str, Any], workspace_root: Path) -> Path:
    workspace = context.get("aiAssistantWorkspace")
    if not isinstance(workspace, dict):
        return workspace_root
    raw_path = (
        workspace.get("cwd")
        or workspace.get("startPath")
        or workspace.get("currentPath")
        or workspace.get("path")
        or ""
    )
    if not isinstance(raw_path, str) or not raw_path.strip():
        return workspace_root
    candidate = Path(raw_path.strip()).expanduser()
    if not candidate.is_absolute():
        candidate = workspace_root / candidate
    try:
        candidate.resolve().relative_to(workspace_root.resolve())
    except ValueError:
        return workspace_root
    return candidate


def _inspector_memory_payload(*, run_input_payload: dict[str, Any], session_context: dict[str, Any]) -> dict[str, Any]:
    memory = memory_payload_from_context(session_context)
    run_memory = run_input_payload.get("memory")
    if isinstance(run_memory, dict) and isinstance(run_memory.get("instructionMemory"), list):
        memory["instructionMemory"] = [dict(item) for item in run_memory["instructionMemory"] if isinstance(item, dict)]
    else:
        memory.setdefault("instructionMemory", [])
    return memory


def _elapsed_duration_ms(started: float) -> int:
    elapsed_ms = max(0.0, (perf_counter() - started) * 1000)
    return max(1, int(ceil(elapsed_ms)))


def _tool_idempotency_key(tool_name: str, payload: dict[str, Any]) -> str:
    case_id = payload.get("caseId") or payload.get("case_id")
    if case_id:
        return f"{tool_name}:{case_id}"
    encoded = json.dumps({"toolName": tool_name, "payload": payload}, sort_keys=True, ensure_ascii=True)
    return f"{tool_name}:{sha256(encoded.encode('utf-8')).hexdigest()[:24]}"


def _tool_record_input(
    payload: dict[str, Any],
    *,
    dispatch_result: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    recorded = dict(payload)
    if extra:
        recorded.update(extra)
    runner_result = dispatch_result.get("runner_result")
    if isinstance(runner_result, ToolRunResult):
        recorded["_toolRuntime"] = {
            "idempotencyKey": runner_result.idempotency_key,
            "attempts": runner_result.attempts,
            "span": runner_result.span,
            "budget": runner_result.budget,
        }
    return recorded


def _tool_result_visible_summary(output: dict[str, Any]) -> str:
    observation = output.get("observation")
    if isinstance(observation, dict):
        error = observation.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error.get("code") or "工具失败 observation")
        return "工具失败 observation"
    for key in ("echo", "path", "skillName", "stdout", "stderr", "message", "status"):
        value = output.get(key)
        if value:
            return str(value)
    return ""


def _tool_runtime_event_title(event_type: str) -> str:
    return {
        "tool.retry_scheduled": "工具重试",
        "tool.fallback_used": "工具降级",
        "tool.circuit_open": "工具熔断",
        "tool.error_observation": "工具失败观察",
        "tool.idempotency_replayed": "工具幂等命中",
        "tool.idempotency_uncertain": "工具幂等不确定",
    }.get(event_type, "工具运行时事件")


def _tool_runtime_event_summary(event_type: str, payload: dict[str, Any]) -> str:
    if event_type == "tool.retry_scheduled":
        return "工具失败后已安排重试。"
    if event_type == "tool.fallback_used":
        return "工具失败后已使用降级 Adapter。"
    if event_type == "tool.circuit_open":
        return "工具熔断器已打开。"
    if event_type == "tool.error_observation":
        observation = payload.get("observation")
        if isinstance(observation, dict):
            error = observation.get("error")
            if isinstance(error, dict):
                return str(error.get("message") or error.get("code") or "工具失败已转为 observation。")
        return "工具失败已转为 observation。"
    if event_type == "tool.idempotency_replayed":
        return "工具幂等键命中，已复用既有结果。"
    if event_type == "tool.idempotency_uncertain":
        return "同一幂等键已有超时尝试，结果不确定，已阻止重复执行。"
    return "工具运行时事件已记录。"


def _skill_audit_event_title(event_type: str) -> str:
    return {
        "skill.load_started": "技能加载开始",
        "skill.loaded": "技能已加载",
        "skill.resource_read": "技能资源读取",
        "skill.script_invoked": "技能脚本调用",
    }.get(event_type, event_type)


def _skill_audit_event_summary(event_type: str, payload: dict[str, Any]) -> str:
    skill_name = str(payload.get("skillName") or "")
    if event_type == "skill.load_started":
        return f"{skill_name} 技能开始按需加载。"
    if event_type == "skill.loaded":
        return f"{skill_name} 技能已按需加载。"
    if event_type == "skill.resource_read":
        return f"{skill_name} 技能资源 {payload.get('path')} 已读取。"
    if event_type == "skill.script_invoked":
        return f"{skill_name} 技能脚本调用已记录。"
    return "技能运行时事件已记录。"


def _supplement_required_tool_calls(message: str, tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    supplemented = [_canonical_tool_call(call) for call in tool_calls]
    seen = {_tool_call_key(call) for call in supplemented}
    tool_names = {str(call.get("toolName") or "") for call in supplemented}
    write_paths = {
        _workspace_path_from_tool_call(call)
        for call in supplemented
        if call.get("toolName") == "write_workspace_file" and _workspace_path_from_tool_call(call)
    }
    staged_read_only_round = bool(supplemented) and tool_names <= {"read_workspace_file"}

    def add(tool_name: str, tool_input: dict[str, Any]) -> None:
        if tool_name in {"search_knowledge_base", "invoke_skill"} and tool_name in tool_names:
            return
        call = {"toolName": tool_name, "toolInput": tool_input}
        if tool_name == "write_workspace_file":
            path = _workspace_path_from_tool_call(call)
            if path in write_paths:
                return
        key = _tool_call_key(call)
        if key in seen:
            return
        supplemented.append(call)
        seen.add(key)
        tool_names.add(tool_name)
        if tool_name == "write_workspace_file":
            path = _workspace_path_from_tool_call(call)
            if path:
                write_paths.add(path)

    if not staged_read_only_round and _mentions_knowledge_search(message):
        add("search_knowledge_base", {"query": _knowledge_query(message)})
    if not staged_read_only_round and _mentions_tdd_or_skill(message):
        add("invoke_skill", {"skillName": _skill_name(message), "instruction": _skill_instruction(message)})

    file_paths = _mentioned_file_paths(message)
    write_path = _write_target_path(message, file_paths)
    for path in _read_target_paths(message, file_paths, write_path):
        add("read_workspace_file", {"path": path})
    if write_path and not staged_read_only_round and _mentions_write_intent(message):
        add("write_workspace_file", {"path": write_path, "content": _write_content(message)})
    if write_path and not staged_read_only_round and _mentions_readback_after_write(message):
        add("read_workspace_file", {"path": write_path})
    return supplemented


def _canonical_tool_call(call: dict[str, Any]) -> dict[str, Any]:
    canonical = {
        "toolName": str(call.get("toolName") or call.get("tool_name") or ""),
        "toolInput": dict(call.get("toolInput") or call.get("tool_input") or {}),
    }
    tool_call_id = call.get("toolCallId") or call.get("tool_call_id")
    if tool_call_id:
        canonical["toolCallId"] = str(tool_call_id)
    return canonical


def _mentioned_file_paths(message: str) -> list[str]:
    paths = re.findall(r"(?<![\w/.-])(?:[\w.-]+/)*[\w.-]+\.(?:md|txt|json|yaml|yml|py|ts|tsx|vue|js|mjs)", message)
    seen: set[str] = set()
    ordered: list[str] = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        ordered.append(path)
    return ordered


def _write_target_path(message: str, file_paths: list[str]) -> str:
    for path in file_paths:
        index = message.find(path)
        window = message[max(0, index - 18) : index + len(path) + 18]
        if _mentions_write_intent(window):
            return path
    for path in file_paths:
        if path.startswith("tmp/"):
            return path
    return file_paths[-1] if file_paths and _mentions_write_intent(message) else ""


def _read_target_paths(message: str, file_paths: list[str], write_path: str) -> list[str]:
    if not re.search(r"读|读取|查看|打开|看看", message):
        return []
    return [path for path in file_paths if path != write_path]


def _mentions_write_intent(message: str) -> bool:
    return bool(re.search(r"创建|写入|保存|生成文件|落盘", message))


def _mentions_readback_after_write(message: str) -> bool:
    return bool(re.search(r"写.*后.*读|写完.*读|读回|读取该文件|再次.*读取|校验", message))


def _mentions_knowledge_search(message: str) -> bool:
    return bool(re.search(r"知识库|检索|查询|查一下|规则", message))


def _mentions_tdd_or_skill(message: str) -> bool:
    return bool(re.search(r"\btdd\b|TDD|测试驱动|红绿重构|skill|技能", message, flags=re.IGNORECASE))


def _skill_name(message: str) -> str:
    if re.search(r"\btdd\b|TDD|测试驱动|红绿重构", message, flags=re.IGNORECASE):
        return "tdd"
    return "general"


def _skill_instruction(message: str) -> str:
    return message[:240]


def _knowledge_query(message: str) -> str:
    quoted = re.findall(r"[“\"]([^”\"]+)[”\"]", message)
    if quoted:
        return str(quoted[0])
    match = re.search(r"(?:知识库|检索|查询|查一下)(?:里|中的|的)?([^，。；;]+)", message)
    query = match.group(1).strip() if match else message[:80].strip()
    query = re.sub(r"^(?:知识库(?:里|里的|中|中的)?|里|里的|中|中的|的)+", "", query).strip()
    return query or "用户请求"


def _write_content(message: str) -> str:
    match = re.search(r"内容(?:为|是|：|:)([^。；;]+)", message)
    if match:
        return match.group(1).strip()
    return "AI Assistant Harness 写入校验"


def _text_chunks(text: str) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return ["工具执行已完成。"]
    if len(stripped) <= 80:
        return [stripped]
    return [stripped[index : index + 80] for index in range(0, len(stripped), 80)]


def _tool_output_summary(tool_call: dict[str, Any]) -> str:
    output = dict(tool_call.get("output") or {})
    observation = output.get("observation")
    if isinstance(observation, dict):
        error = observation.get("error")
        if isinstance(error, dict):
            return f"{observation.get('toolName') or tool_call.get('toolName')} failed: {error.get('code')}"
    for key in ("echo", "path", "skillName", "stdout", "stderr", "message", "status"):
        value = output.get(key)
        if value:
            return str(value)
    status = str(tool_call.get("status") or "")
    return status


def _tool_call_failed_with_observation(tool_call: dict[str, Any]) -> bool:
    output = tool_call.get("output")
    return tool_call.get("status") == "FAILED" and isinstance(output, dict) and isinstance(output.get("observation"), dict)


def _tool_failure_reason(tool_call: dict[str, Any]) -> str:
    output = dict(tool_call.get("output") or {})
    observation = output.get("observation")
    if isinstance(observation, dict):
        error = observation.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error.get("code") or "tool_error")
    return "tool_error"


def _tool_execution_answer(recorded_tool_calls: list[dict[str, Any]]) -> str:
    tool_summary = "; ".join(
        _tool_output_summary(call) for call in recorded_tool_calls if _tool_output_summary(call)
    )
    return f"工具结果：{tool_summary}" if tool_summary else "工具执行已完成。"


def _new_live_tool_calls(
    tool_calls: list[dict[str, Any]],
    *,
    seen_tool_keys: set[str],
    written_paths: set[str],
    read_after_write_keys: set[str],
) -> list[dict[str, Any]]:
    planned_write_paths: set[str] = set()
    new_calls: list[dict[str, Any]] = []
    for call in tool_calls:
        tool_name = str(call.get("toolName") or "")
        path = _workspace_path_from_tool_call(call)
        key = _tool_call_key(call)
        if tool_name == "write_workspace_file" and path in written_paths:
            planned_write_paths.add(path)
            continue
        if key not in seen_tool_keys:
            new_calls.append(call)
            if tool_name == "write_workspace_file" and path:
                planned_write_paths.add(path)
            continue
        if (
            tool_name == "read_workspace_file"
            and path
            and key not in read_after_write_keys
            and (path in written_paths or path in planned_write_paths)
        ):
            new_calls.append(call)
            read_after_write_keys.add(key)
    return new_calls


def _workspace_path_from_tool_call(tool_call: dict[str, Any]) -> str:
    tool_input = tool_call.get("toolInput") or {}
    if not isinstance(tool_input, dict):
        return ""
    path = tool_input.get("path")
    return str(path) if path else ""


def _written_workspace_paths(recorded_tool_calls: list[dict[str, Any]]) -> set[str]:
    paths: set[str] = set()
    for call in recorded_tool_calls:
        if call.get("toolName") != "write_workspace_file":
            continue
        path = _workspace_path_from_tool_call({"toolInput": call.get("input") or {}})
        if path:
            paths.add(path)
    return paths


def _tool_call_key(tool_call: dict[str, Any]) -> str:
    return json.dumps(
        {
            "toolName": tool_call.get("toolName"),
            "toolInput": tool_call.get("toolInput") or {},
        },
        sort_keys=True,
        ensure_ascii=True,
    )


def _react_messages_after_tools(
    messages: list[ChatRequestMessage],
    decision: LivePlannerDecision,
    requested_tool_calls: list[dict[str, Any]],
    recorded_tool_calls: list[dict[str, Any]],
) -> list[ChatRequestMessage]:
    return [
        *messages,
        ChatRequestMessage(
            role="assistant",
            content=decision.final_answer or None,
            tool_calls=[_assistant_tool_call_payload(call) for call in requested_tool_calls],
        ),
        *[
            _tool_result_message(requested_call, recorded_call)
            for requested_call, recorded_call in zip(requested_tool_calls, recorded_tool_calls, strict=False)
        ],
    ]


def _assistant_tool_call_payload(tool_call: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(tool_call.get("toolCallId") or f"call_{tool_call.get('toolName') or 'tool'}"),
        "type": "function",
        "function": {
            "name": str(tool_call.get("toolName") or ""),
            "arguments": json.dumps(tool_call.get("toolInput") or {}, ensure_ascii=False),
        },
    }


def _tool_result_message(requested_call: dict[str, Any], recorded_call: dict[str, Any]) -> ChatRequestMessage:
    content = {
        "toolName": recorded_call.get("toolName") or requested_call.get("toolName"),
        "status": recorded_call.get("status"),
        "input": recorded_call.get("input") or requested_call.get("toolInput") or {},
        "output": recorded_call.get("output") or {},
    }
    return ChatRequestMessage(
        role="tool",
        content=json.dumps(content, ensure_ascii=False),
        tool_call_id=str(requested_call.get("toolCallId") or f"call_{requested_call.get('toolName') or 'tool'}"),
        name=str(requested_call.get("toolName") or ""),
    )


def _merged_usage(decisions: list[LivePlannerDecision]) -> dict[str, int]:
    totals = {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0}
    for decision in decisions:
        usage = decision.usage
        totals["inputTokens"] += int(usage.get("inputTokens") or usage.get("prompt_tokens") or 0)
        totals["outputTokens"] += int(usage.get("outputTokens") or usage.get("completion_tokens") or 0)
        total = int(usage.get("totalTokens") or usage.get("total_tokens") or 0)
        totals["totalTokens"] += total or (
            int(usage.get("inputTokens") or usage.get("prompt_tokens") or 0)
            + int(usage.get("outputTokens") or usage.get("completion_tokens") or 0)
        )
    return totals


def _schedule_payload(plan: Any) -> dict[str, Any]:
    return {
        "batches": [
            {
                "batchId": batch.batch_id,
                "executionMode": batch.execution_mode,
                "toolNames": [item.tool_name for item in batch.items],
                "readResources": batch.read_resources,
                "writeResources": batch.write_resources,
                "lockMode": batch.lock_mode,
                "resourceLockReason": batch.resource_lock_reason,
                "parallelEligible": batch.parallel_eligible,
            }
            for batch in plan.batches
        ]
    }


def _remaining_scheduled_tool_calls(
    batches: list[Any],
    current_batch_index: int,
    current_item_index: int,
) -> list[dict[str, Any]]:
    remaining: list[dict[str, Any]] = []
    for batch_index, batch in enumerate(batches):
        start_index = current_item_index + 1 if batch_index == current_batch_index else 0
        if batch_index < current_batch_index:
            continue
        for item in batch.items[start_index:]:
            remaining.append({"toolName": item.tool_name, "toolInput": dict(item.tool_input or {})})
    return remaining


def _pending_tool_calls_after_approval(response_payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_calls = response_payload.get("pendingToolCallsAfterApproval")
    if not isinstance(raw_calls, list):
        return []
    return _scheduled_tool_calls([call for call in raw_calls if isinstance(call, dict)])


def _safe_model_config_payload(model_config: LivePlannerConfig | None) -> dict[str, Any] | None:
    if model_config is None:
        return None
    return {
        "provider": model_config.provider,
        "baseUrl": model_config.base_url,
        "model": model_config.model,
        "apiKeyRef": model_config.api_key_ref,
        "hasApiKey": bool(model_config.api_key),
        "temperature": model_config.temperature,
        "maxTokens": model_config.max_tokens,
    }


def _model_config_from_request_payload(request: dict[str, Any]) -> LivePlannerConfig | None:
    payload = request.get("modelConfig")
    if not isinstance(payload, dict):
        return None
    base_url = str(payload.get("baseUrl") or "").strip()
    model = str(payload.get("model") or "").strip()
    if not base_url or not model:
        return None
    return LivePlannerConfig(
        provider=str(payload.get("provider") or "openrouter"),
        base_url=base_url,
        model=model,
        api_key="",
        api_key_ref=str(payload.get("apiKeyRef") or "env:OPENROUTER_API_KEY"),
        temperature=float(payload.get("temperature") or 0),
        max_tokens=int(payload.get("maxTokens") or 1024),
    )


def _worker_execution_model_config(
    request: dict[str, Any],
    worker_model_config: LivePlannerConfig | None,
) -> LivePlannerConfig | None:
    queued_model_config = _model_config_from_request_payload(request)
    if worker_model_config is None:
        return queued_model_config
    queued_payload = request.get("modelConfig")
    if isinstance(queued_payload, dict):
        queued_fingerprint = _model_config_fingerprint(queued_payload)
        worker_fingerprint = _model_config_fingerprint(_safe_model_config_payload(worker_model_config) or {})
        if queued_fingerprint != worker_fingerprint:
            raise RunControlConflict("Worker modelConfig does not match queued run modelConfig")
    return worker_model_config


def _model_config_fingerprint(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider": str(payload.get("provider") or "openrouter"),
        "baseUrl": str(payload.get("baseUrl") or ""),
        "model": str(payload.get("model") or ""),
        "apiKeyRef": str(payload.get("apiKeyRef") or "env:OPENROUTER_API_KEY"),
        "temperature": float(payload.get("temperature") or 0),
        "maxTokens": int(payload.get("maxTokens") or 1024),
    }


def _live_requested(model_mode: str) -> bool:
    return model_mode.strip().lower() in {"live", "qwen", "openrouter"}


def _scheduled_tool_calls(tool_calls: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    canonical: list[dict[str, Any]] = []
    for call in tool_calls or []:
        tool_name = str(call.get("toolName") or call.get("tool_name") or "")
        if not tool_name:
            continue
        canonical.append(
            {
                "toolName": tool_name,
                "toolInput": dict(call.get("toolInput") or call.get("tool_input") or {}),
            }
        )
    return canonical


def _tool_call_payload(tool_call: dict[str, Any]) -> dict[str, Any]:
    input_payload = tool_call.get("input_payload") or {}
    scheduler = dict(input_payload.get("_scheduler") or {})
    return {
        "id": tool_call["id"],
        "toolName": tool_call["tool_name"],
        "input": {key: value for key, value in input_payload.items() if key != "_scheduler"},
        "output": tool_call.get("output_payload") or {},
        "status": tool_call["status"],
        "durationMs": tool_call["duration_ms"],
        "scheduler": scheduler,
    }


def _manifest_payload(manifest: Any) -> dict[str, Any]:
    return {
        "name": manifest.name,
        "description": manifest.description,
        "inputSchema": manifest.input_schema,
        "outputSchema": manifest.output_schema,
        "timeoutMs": manifest.timeout_ms,
        "riskLevel": manifest.risk_level.value,
        "readResources": manifest.read_resources,
        "writeResources": manifest.write_resources,
        "policyRef": manifest.policy_ref,
    }


def _approval_payload(approval: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": approval["id"],
        "sessionId": approval["session_id"],
        "runId": approval["run_id"],
        "toolName": approval["tool_name"],
        "riskLevel": approval["risk_level"],
        "input": approval.get("input_payload") or {},
        "status": approval["status"],
        "decidedBy": approval.get("decided_by"),
        "decisionReason": approval.get("decision_reason") or "",
    }


def _run_payload(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": run["id"],
        "sessionId": run["session_id"],
        "status": run["status"],
        "input": run.get("input_payload") or {},
        "result": run.get("response_payload") or {},
        "startedAt": run["started_at"].isoformat() if run.get("started_at") else None,
        "completedAt": run["completed_at"].isoformat() if run.get("completed_at") else None,
    }


def _plan_payload_from_run(run: dict[str, Any]) -> dict[str, Any]:
    response_payload = dict(run.get("response_payload") or {})
    input_payload = dict(run.get("input_payload") or {})
    plan = response_payload.get("plan") or input_payload.get("plan") or {}
    return dict(plan) if isinstance(plan, dict) else {}


def _task_payload(
    run: dict[str, Any],
    events: list[dict[str, Any]],
    approvals: list[dict[str, Any]],
) -> dict[str, Any]:
    last_event = events[-1] if events else None
    pending_approval = next((approval for approval in approvals if approval["status"] == "PENDING"), None)
    message = str((run.get("input_payload") or {}).get("message") or "助手运行")
    title = message if len(message) <= 80 else f"{message[:77]}..."
    phase = "等待审批" if pending_approval else _phase_label(str((last_event or {}).get("type") or "created"))
    plan = _plan_payload_from_run(run)
    current_step = plan.get("currentStep") if isinstance(plan.get("currentStep"), dict) else None
    planned_tools = [
        str(tool_name)
        for tool_name in plan.get("plannedTools", [])
        if tool_name
    ]
    return {
        "id": f"run-{run['id']}",
        "runId": run["id"],
        "planId": plan.get("id"),
        "planningStrategy": plan.get("planningStrategy") or "auto_lightweight",
        "title": title,
        "status": run["status"],
        "phase": phase,
        "currentTool": pending_approval["tool_name"] if pending_approval else (current_step or {}).get("toolName"),
        "recognizedNeeds": plan.get("recognizedNeeds") or [],
        "plannedTools": planned_tools,
        "currentStep": current_step,
        "finalResult": plan.get("finalResult") or "",
        "updatedAt": (
            run["completed_at"].isoformat()
            if run.get("completed_at")
            else run["updated_at"].isoformat()
            if run.get("updated_at")
            else None
        ),
    }


def _event_timeline_payload(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": event["id"],
        "sequence": event["sequence"],
        "type": event["type"],
        "status": event["status"],
        "level": event["level"],
        "title": event["visible_title"],
        "summary": event["visible_summary"],
        "createdAt": event["created_at"].isoformat(),
    }


def _recent_error_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    error_types = {"model.call_failed", "tool.call_failed", "approval.denied", "sandbox.denied", "run.failed"}
    return [
        event
        for event in events
        if event["type"] in error_types or event["level"] == "error" or event["status"] in {"DENIED", "FAILED"}
    ][-5:]


def _phase_label(event_type: str) -> str:
    labels = {
        "created": "已创建",
        "run.started": "运行开始",
        "orchestration.phase_started": "推理规划",
        "model.call_started": "模型调用",
        "model.thought_summary": "思考摘要",
        "model.stream_chunk": "模型输出",
        "model.tool_call_decision": "工具决策",
        "model.file_intent": "文件意图",
        "model.skill_intent": "技能意图",
        "task.updated": "任务编排",
        "scheduler.batch_started": "工具批次",
        "tool.call_started": "工具执行",
        "tool.call_output": "工具输出",
        "tool.call_completed": "工具完成",
        "skill.load_started": "技能加载开始",
        "skill.loaded": "技能已加载",
        "skill.resource_read": "技能资源读取",
        "skill.script_invoked": "技能脚本调用",
        "approval.required": "等待审批",
        "proposed_action.created": "拟执行动作",
        "run.completed": "运行完成",
        "sandbox.denied": "沙箱拒绝",
    }
    return labels.get(event_type, event_type)


def _tool_label(tool_name: str) -> str:
    labels = {
        "echo_context": "上下文回显",
        "update_customer_profile": "客户资料变更",
        "run_shell": "Shell 执行",
        "customer_assistant_subagent_bridge": "客服助手子任务桥接",
        "read_workspace_file": "读取工作区文件",
        "list_workspace_files": "列出工作区文件",
        "search_workspace_files": "搜索工作区文件",
        "edit_workspace_file": "编辑工作区文件",
        "write_workspace_file": "写入工作区文件",
        "apply_workspace_patch": "应用工作区补丁",
        "invoke_skill": "调用技能",
        "read_skill_resource": "读取技能资源",
        "run_skill_script": "运行技能脚本",
        "search_knowledge_base": "知识库检索",
    }
    return labels.get(tool_name, tool_name)


def _turn_result_from_run(run: dict[str, Any]) -> HarnessTurnResult:
    response = dict(run.get("response_payload") or {})
    return HarnessTurnResult(
        run=run,
        replayed=False,
        final_answer=str(response.get("finalAnswer") or ""),
        tool_calls=list(response.get("toolCalls") or []),
        approval_required=bool(response.get("approvalRequired") or False),
        approval_id=response.get("approvalId"),
        sandbox_denied=bool(response.get("sandboxDenied") or False),
    )


def _runtime_checkpoint_from_run(run: dict[str, Any]) -> dict[str, Any]:
    runtime = dict((run.get("input_payload") or {}).get("sessionRuntime") or {})
    checkpoint = runtime.get("checkpoint")
    return dict(checkpoint) if isinstance(checkpoint, dict) else {}


def _runtime_phase_for_status(status: str) -> str:
    return {
        "QUEUED": "queued",
        "RUNNING": "running",
        "PAUSED": "paused",
        "CANCELLED": "cancelled",
        "WAITING_APPROVAL": "waiting_approval",
        "COMPLETED": "finalized",
        "FAILED": "failed",
        "DENIED": "denied",
    }.get(status, status.lower())


def _control_event_type(action: str) -> str:
    return {
        "pause": "run.paused",
        "resume": "run.resumed",
        "cancel": "run.cancelled",
    }.get(action, f"run.{action}")


def _control_event_title(action: str) -> str:
    return {
        "pause": "运行已暂停",
        "resume": "运行已恢复",
        "cancel": "运行已取消",
    }.get(action, "运行控制已更新")


def _control_event_summary(action: str) -> str:
    return {
        "pause": "SessionRuntime 已暂停该运行。",
        "resume": "SessionRuntime 已将该运行重新入队。",
        "cancel": "SessionRuntime 已取消该运行。",
    }.get(action, "SessionRuntime 已更新运行控制状态。")


def _last_event_sequence(repository: AiAssistantRepository, run_id: int) -> int:
    events = repository.list_run_events(run_id)
    if not events:
        return 0
    return max(int(event.get("sequence") or 0) for event in events)


def _usage_payload(run: dict[str, Any]) -> dict[str, Any]:
    started_at = run.get("started_at")
    ended_at = run.get("completed_at") or run.get("updated_at")
    elapsed_ms = 0
    if started_at is not None and ended_at is not None:
        elapsed_ms = max(0, int((ended_at - started_at).total_seconds() * 1000))
    return {
        "inputTokens": 0,
        "outputTokens": 0,
        "totalTokens": 0,
        "elapsedMs": elapsed_ms,
    }
