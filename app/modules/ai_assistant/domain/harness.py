from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from hashlib import sha256
import json
from math import ceil
import re
from time import perf_counter
from typing import Any

from app.modules.ai_assistant.domain.live_model import LivePlannerConfig, LivePlannerDecision, QwenLivePlanner
from app.modules.ai_assistant.domain.observability import build_observability_snapshot
from app.modules.ai_assistant.domain.permissions import ApprovalMode, ApprovalPolicy, PermissionDecision
from app.modules.ai_assistant.domain.prompt import PromptAssembler
from app.modules.ai_assistant.domain.sandbox import SandboxPolicy, SandboxVerdict
from app.modules.ai_assistant.domain.scheduler import ScheduledToolInvocation, ToolScheduler
from app.modules.ai_assistant.domain.tools import ToolRegistry
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
    ) -> None:
        self._repository = repository
        self._tools = tool_registry or ToolRegistry.with_builtin_tools()
        self._approval_policy = approval_policy or ApprovalPolicy(environment="test")
        self._sandbox_policy = sandbox_policy or SandboxPolicy()
        self._live_planner = live_planner

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
        tool_name: str = "echo_context",
        tool_input: dict[str, Any] | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        model_mode: str = "deterministic",
        model_config: LivePlannerConfig | None = None,
    ) -> HarnessTurnResult:
        started = self.start_message(
            session_id=session_id,
            message=message,
            idempotency_key=idempotency_key,
            approval_mode=approval_mode,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_calls=tool_calls,
            model_mode=model_mode,
            model_config=model_config,
        )
        if started.replayed or started.run["status"] != "RUNNING":
            return started
        return self.complete_started_message(
            session_id=session_id,
            run_id=int(started.run["id"]),
            run=started.run,
            message=message,
            approval_mode=approval_mode,
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
        tool_name: str = "echo_context",
        tool_input: dict[str, Any] | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        model_mode: str = "deterministic",
        model_config: LivePlannerConfig | None = None,
    ) -> HarnessTurnResult:
        payload = tool_input or {"message": message}
        scheduled_tool_calls = _scheduled_tool_calls(tool_calls)
        request_hash = _request_hash(
            {
                "message": message,
                "approvalMode": approval_mode,
                "toolName": tool_name,
                "toolInput": payload,
                "toolCalls": scheduled_tool_calls,
                "modelMode": model_mode,
                "modelConfig": _safe_model_config_payload(model_config),
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
        self._repository.append_message(session_id, "user", message, run_id=run_id)
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="run.started",
            visible_title="运行开始",
            visible_summary="AI 助手运行已开始。",
            payload={"phase": "reason"},
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="orchestration.phase_started",
            visible_title="推理规划",
            visible_summary="正在选择模型与工具编排路径。",
            payload={
                "phase": "reason",
                "promptLayers": [
                    layer["name"]
                    for layer in PromptAssembler(
                        base_instruction="You are Hify AI Assistant.",
                        tool_registry=self._tools,
                    )
                    .assemble(
                        user_message=message,
                        run_state={"status": "RUNNING", "phase": "reason"},
                    )
                    .layers
                ],
                "modelConfig": _safe_model_config_payload(model_config),
            },
        )
        return HarnessTurnResult(run=run, replayed=False, final_answer="", tool_calls=[])

    def complete_started_message(
        self,
        *,
        session_id: int,
        run_id: int,
        run: dict[str, Any] | None = None,
        message: str,
        approval_mode: str = ApprovalMode.SMART_APPROVAL.value,
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
        if scheduled_tool_calls:
            return self._run_scheduled_tool_calls(
                session_id=session_id,
                run_id=run_id,
                run=current_run,
                message=message,
                approval_mode=approval_mode,
                tool_calls=scheduled_tool_calls,
            )
        manifest = self._tools.get_manifest(tool_name)
        sandbox_decision = self._sandbox_policy.evaluate(tool_name, payload)
        if sandbox_decision.verdict == SandboxVerdict.DENY:
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
            }
            denied = self._repository.complete_run(run_id, response_payload, status="DENIED")
            return HarnessTurnResult(
                run=denied,
                replayed=False,
                final_answer=str(response_payload["finalAnswer"]),
                tool_calls=[],
                sandbox_denied=True,
            )

        permission = self._approval_policy.decide(
            approval_mode=ApprovalMode(approval_mode),
            risk_level=manifest.risk_level,
        )
        if permission == PermissionDecision.DENY:
            response_payload = {
                "finalAnswer": "审批策略已拒绝该工具请求。",
                "toolCalls": [],
                "approvalRequired": False,
                "sandboxDenied": False,
            }
            denied = self._repository.complete_run(run_id, response_payload, status="DENIED")
            return HarnessTurnResult(
                run=denied,
                replayed=False,
                final_answer=str(response_payload["finalAnswer"]),
                tool_calls=[],
            )
        if permission == PermissionDecision.REQUIRE_APPROVAL:
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
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="tool.call_started",
            visible_title="工具开始",
            visible_summary=f"{_tool_label(tool_name)} 已开始执行。",
            payload={"toolName": tool_name, "input": payload},
        )
        started = perf_counter()
        dispatch_payload = payload | {"message": str(payload.get("message") or message)}
        if tool_name == "echo_context":
            dispatch_payload = dispatch_payload | {"context": {"sessionId": session_id}}
        tool_result = self._tools.dispatch(tool_name, dispatch_payload)
        duration_ms = _elapsed_duration_ms(started)
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="tool.call_output",
            visible_title="工具输出",
            visible_summary=str(tool_result.output.get("echo") or ""),
            payload={"toolName": tool_name, "output": tool_result.output},
        )
        tool_call = self._repository.record_tool_call(
            run_id=run_id,
            session_id=session_id,
            tool_name=tool_name,
            input_payload=payload,
            output_payload=tool_result.output,
            status=tool_result.status,
            duration_ms=duration_ms,
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
        final_answer = f"回显结果：{tool_result.output.get('echo', '')}"
        self._repository.append_message(session_id, "assistant", final_answer, run_id=run_id)
        response_payload = {
            "finalAnswer": final_answer,
            "toolCalls": [_tool_call_payload(tool_call)],
            "approvalRequired": False,
            "sandboxDenied": False,
        }
        completed = self._repository.complete_run(run_id, response_payload)
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="run.completed",
            visible_title="运行完成",
            visible_summary="AI 助手运行已完成。",
            payload={"finalAnswer": final_answer},
        )
        return HarnessTurnResult(
            run=completed,
            replayed=False,
            final_answer=final_answer,
            tool_calls=[_tool_call_payload(tool_call)],
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
            streamed_count = max(streamed_count, index)
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

            new_tool_calls = [call for call in decision.tool_calls if _tool_call_key(call) not in seen_tool_keys]
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
            )
            recorded_tool_calls.extend(execution.recorded_tool_calls)
            if execution.terminal_result is not None:
                return self._with_accumulated_tool_calls(execution.terminal_result, recorded_tool_calls)
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
        response_payload = {
            "finalAnswer": final_answer,
            "toolCalls": recorded_tool_calls,
            "approvalRequired": False,
            "sandboxDenied": False,
            "model": {"provider": decision.provider, "model": decision.model, "usage": _merged_usage(decisions)},
        }
        completed = self._repository.complete_run(run_id, response_payload)
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
        failed = self._repository.complete_run(
            run_id,
            {
                "finalAnswer": reason,
                "toolCalls": [],
                "approvalRequired": False,
                "sandboxDenied": False,
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
                event_type="model.stream_chunk",
                visible_title="模型输出",
                visible_summary=chunk,
                payload={
                    "index": index,
                    "chunk": chunk,
                    "model": model,
                    "phase": phase,
                    "streaming": True,
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
                recorded_tool_calls.extend(
                    self._run_read_parallel_batch(
                        session_id=session_id,
                        run_id=run_id,
                        message=message,
                        batch=batch,
                    )
                )
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
                    )
                    if isinstance(result, HarnessTurnResult):
                        return ScheduledToolExecutionResult(
                            recorded_tool_calls=recorded_tool_calls,
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
        self._append_model_output_stream(
            run_id=run_id,
            session_id=session_id,
            model=model_decision.model if model_decision else "deterministic",
            text=final_answer,
            phase="final_answer",
            source="harness_final_answer",
        )
        self._repository.append_message(session_id, "assistant", final_answer, run_id=run_id)
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
        }
        completed = self._repository.complete_run(run_id, response_payload)
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
        batch: Any,
    ) -> list[dict[str, Any]]:
        for index, item in enumerate(batch.items):
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
                    session_id=session_id,
                    message=message,
                    tool_name=item.tool_name,
                    payload=item.tool_input,
                )
                for item in batch.items
            ]
            dispatch_results = [future.result() for future in futures]

        recorded: list[dict[str, Any]] = []
        for index, (item, dispatch_result) in enumerate(zip(batch.items, dispatch_results, strict=True)):
            scheduler_metadata = batch.item_metadata[index]
            tool_result = dispatch_result["tool_result"]
            self._repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type="tool.call_output",
                visible_title="工具输出",
                visible_summary=str(tool_result.output.get("echo") or ""),
                payload={"toolName": item.tool_name, "output": tool_result.output, "scheduler": scheduler_metadata},
                correlation_ids={"scheduler": scheduler_metadata},
            )
            tool_call = self._repository.record_tool_call(
                run_id=run_id,
                session_id=session_id,
                tool_name=item.tool_name,
                input_payload={**item.tool_input, "_scheduler": scheduler_metadata},
                output_payload=tool_result.output,
                status=tool_result.status,
                duration_ms=int(dispatch_result["duration_ms"]),
            )
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
            recorded.append(_tool_call_payload(tool_call))
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
    ) -> dict[str, Any] | HarnessTurnResult:
        manifest = self._tools.get_manifest(tool_name)
        sandbox_decision = self._sandbox_policy.evaluate(tool_name, payload)
        if sandbox_decision.verdict == SandboxVerdict.DENY:
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
            }
            denied = self._repository.complete_run(run_id, response_payload, status="DENIED")
            return HarnessTurnResult(
                run=denied,
                replayed=False,
                final_answer=str(response_payload["finalAnswer"]),
                tool_calls=[],
                sandbox_denied=True,
            )
        permission = self._approval_policy.decide(
            approval_mode=ApprovalMode(approval_mode),
            risk_level=manifest.risk_level,
        )
        if permission == PermissionDecision.REQUIRE_APPROVAL:
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
            session_id=session_id,
            message=message,
            tool_name=tool_name,
            payload=payload,
        )
        tool_result = dispatch_result["tool_result"]
        duration_ms = int(dispatch_result["duration_ms"])
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="tool.call_output",
            visible_title="工具输出",
            visible_summary=str(tool_result.output.get("echo") or ""),
            payload={"toolName": tool_name, "output": tool_result.output, "scheduler": scheduler_metadata},
            correlation_ids={"scheduler": scheduler_metadata},
        )
        tool_call = self._repository.record_tool_call(
            run_id=run_id,
            session_id=session_id,
            tool_name=tool_name,
            input_payload={**payload, "_scheduler": scheduler_metadata},
            output_payload=tool_result.output,
            status=tool_result.status,
            duration_ms=duration_ms,
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
        return _tool_call_payload(tool_call)

    def _dispatch_tool(
        self,
        *,
        session_id: int,
        message: str,
        tool_name: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        started = perf_counter()
        dispatch_payload = payload | {"message": str(payload.get("message") or message)}
        if tool_name == "echo_context":
            dispatch_payload = dispatch_payload | {"context": {"sessionId": session_id}}
        tool_result = self._tools.dispatch(tool_name, dispatch_payload)
        return {
            "tool_result": tool_result,
            "duration_ms": _elapsed_duration_ms(started),
        }

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
        return {
            "run": _run_payload(run),
            "activeTasks": [_task_payload(run, events, approvals)],
            "toolCalls": [_tool_call_payload(row) for row in tool_calls],
            "approvalQueue": [_approval_payload(row) for row in pending_approvals],
            "approvalHistory": [_approval_payload(row) for row in approvals],
            "recentErrors": [_event_timeline_payload(row) for row in _recent_error_events(events)],
            "eventTimeline": [_event_timeline_payload(row) for row in events],
            "usage": observability["usage"],
            "observability": observability,
        }

    def list_tool_manifests(self) -> list[dict[str, Any]]:
        return [_manifest_payload(manifest) for manifest in self._tools.list_manifests()]

    def list_pending_approvals(self) -> list[dict[str, Any]]:
        return [_approval_payload(row) for row in self._repository.list_pending_approvals()]

    def approve(self, approval_id: int, actor_id: str) -> dict[str, Any]:
        current = self._repository.get_approval(approval_id)
        if current is None:
            raise KeyError(f"AI Assistant approval not found: {approval_id}")
        if current["status"] != "PENDING":
            return _approval_payload(current)
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
        run = self._repository.get_run(run_id)
        if run is None:
            raise KeyError(f"AI Assistant run not found: {run_id}")
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
        self._repository.append_message(session_id, "assistant", final_answer, run_id=run_id)
        response_payload = {
            "finalAnswer": final_answer,
            "toolCalls": tool_calls,
            "approvalRequired": False,
            "approvalId": approval_id,
            "sandboxDenied": False,
            "pendingToolCallsAfterApproval": [],
        }
        self._repository.complete_run(run_id, response_payload)
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="run.completed",
            visible_title="运行完成",
            visible_summary="审批通过的工具已执行，AI 助手运行已完成。",
            payload={"finalAnswer": final_answer},
        )
        return _approval_payload(approval)

    def deny(self, approval_id: int, actor_id: str, reason: str = "") -> dict[str, Any]:
        current = self._repository.get_approval(approval_id)
        if current is None:
            raise KeyError(f"AI Assistant approval not found: {approval_id}")
        if current["status"] != "PENDING":
            return _approval_payload(current)
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
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="tool.call_started",
            visible_title="工具开始",
            visible_summary=f"{_tool_label(tool_name)} 已开始执行。",
            payload={"toolName": tool_name, "input": payload, "approvalResumed": True},
        )
        dispatch_result = self._dispatch_tool(
            session_id=session_id,
            message=message,
            tool_name=tool_name,
            payload=payload,
        )
        tool_result = dispatch_result["tool_result"]
        duration_ms = int(dispatch_result["duration_ms"])
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="tool.call_output",
            visible_title="工具输出",
            visible_summary=str(tool_result.output.get("echo") or tool_result.output.get("path") or ""),
            payload={"toolName": tool_name, "output": tool_result.output, "approvalResumed": True},
        )
        tool_call = self._repository.record_tool_call(
            run_id=run_id,
            session_id=session_id,
            tool_name=tool_name,
            input_payload=payload,
            output_payload=tool_result.output,
            status=tool_result.status,
            duration_ms=duration_ms,
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="tool.call_completed",
            visible_title="工具完成",
            visible_summary=f"{_tool_label(tool_name)} 已完成。",
            payload={"toolName": tool_name, "status": tool_result.status, "approvalResumed": True},
            tool_call_id=int(tool_call["id"]),
        )
        return _tool_call_payload(tool_call)


def _request_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return sha256(encoded.encode("utf-8")).hexdigest()


def _elapsed_duration_ms(started: float) -> int:
    elapsed_ms = max(0.0, (perf_counter() - started) * 1000)
    return max(1, int(ceil(elapsed_ms)))


def _supplement_required_tool_calls(message: str, tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    supplemented = [_canonical_tool_call(call) for call in tool_calls]
    seen = {_tool_call_key(call) for call in supplemented}
    tool_names = {str(call.get("toolName") or "") for call in supplemented}
    staged_read_only_round = bool(supplemented) and tool_names <= {"read_workspace_file"}

    def add(tool_name: str, tool_input: dict[str, Any]) -> None:
        if tool_name in {"search_knowledge_base", "invoke_skill"} and tool_name in tool_names:
            return
        call = {"toolName": tool_name, "toolInput": tool_input}
        key = _tool_call_key(call)
        if key in seen:
            return
        supplemented.append(call)
        seen.add(key)
        tool_names.add(tool_name)

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
        return quoted[0]
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
    for key in ("echo", "path", "skillName", "status"):
        value = output.get(key)
        if value:
            return str(value)
    status = str(tool_call.get("status") or "")
    return status


def _tool_execution_answer(recorded_tool_calls: list[dict[str, Any]]) -> str:
    tool_summary = "; ".join(
        _tool_output_summary(call) for call in recorded_tool_calls if _tool_output_summary(call)
    )
    return f"工具结果：{tool_summary}" if tool_summary else "工具执行已完成。"


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
    return {
        "id": f"run-{run['id']}",
        "runId": run["id"],
        "title": title,
        "status": run["status"],
        "phase": phase,
        "currentTool": pending_approval["tool_name"] if pending_approval else None,
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
        "write_workspace_file": "写入工作区文件",
        "invoke_skill": "调用技能",
        "search_knowledge_base": "知识库检索",
    }
    return labels.get(tool_name, tool_name)


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
