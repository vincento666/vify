from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from time import perf_counter
from typing import Any

from app.modules.ai_assistant.domain.permissions import ApprovalMode, ApprovalPolicy, PermissionDecision
from app.modules.ai_assistant.domain.prompt import PromptAssembler
from app.modules.ai_assistant.domain.sandbox import SandboxPolicy, SandboxVerdict
from app.modules.ai_assistant.domain.tools import ToolRegistry
from app.modules.ai_assistant.infra.repository import AiAssistantRepository, IdempotencyConflict


@dataclass(frozen=True)
class HarnessTurnResult:
    run: dict[str, Any]
    replayed: bool
    final_answer: str
    tool_calls: list[dict[str, Any]]
    approval_required: bool = False
    approval_id: int | None = None
    sandbox_denied: bool = False


class AiAssistantHarnessService:
    def __init__(
        self,
        repository: AiAssistantRepository,
        tool_registry: ToolRegistry | None = None,
        approval_policy: ApprovalPolicy | None = None,
        sandbox_policy: SandboxPolicy | None = None,
    ) -> None:
        self._repository = repository
        self._tools = tool_registry or ToolRegistry.with_builtin_tools()
        self._approval_policy = approval_policy or ApprovalPolicy(environment="test")
        self._sandbox_policy = sandbox_policy or SandboxPolicy()

    def create_session(self, title: str = "", context: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._repository.create_session(title=title, context=context)

    def list_sessions(self) -> list[dict[str, Any]]:
        return self._repository.list_sessions()

    def get_session(self, session_id: int) -> dict[str, Any] | None:
        return self._repository.get_session(session_id)

    def run_message(
        self,
        session_id: int,
        message: str,
        idempotency_key: str | None = None,
        approval_mode: str = ApprovalMode.SMART_APPROVAL.value,
        tool_name: str = "echo_context",
        tool_input: dict[str, Any] | None = None,
    ) -> HarnessTurnResult:
        payload = tool_input or {"message": message}
        request_hash = _request_hash(
            {
                "message": message,
                "approvalMode": approval_mode,
                "toolName": tool_name,
                "toolInput": payload,
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
            visible_title="Run started",
            visible_summary="The assistant run started.",
            payload={"phase": "reason"},
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="orchestration.phase_started",
            visible_title="Reason",
            visible_summary="The harness selected a read-only tool path.",
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
            },
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="model.call_completed",
            visible_title="Model decision",
            visible_summary="The deterministic MVP planner selected echo_context.",
            payload={"toolName": "echo_context"},
        )
        manifest = self._tools.get_manifest(tool_name)
        sandbox_decision = self._sandbox_policy.evaluate(tool_name, payload)
        if sandbox_decision.verdict == SandboxVerdict.DENY:
            self._repository.append_event(
                run_id=run_id,
                session_id=session_id,
                event_type="sandbox.denied",
                visible_title="Sandbox denied",
                visible_summary=sandbox_decision.reason,
                payload=sandbox_decision.evidence,
                status="DENIED",
            )
            response_payload = {
                "finalAnswer": "Sandbox denied the requested tool.",
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
                "finalAnswer": "Approval policy denied the requested tool.",
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
                visible_title="Approval required",
                visible_summary=f"{tool_name} requires approval.",
                payload={"approvalId": approval["id"], "toolName": tool_name, "riskLevel": manifest.risk_level.value},
                status="WAITING",
            )
            if manifest.risk_level.value == "BUSINESS_WRITE":
                proposed_action = self._repository.create_proposed_action(
                    run_id=run_id,
                    session_id=session_id,
                    approval_id=int(approval["id"]),
                    action_type=tool_name,
                    title=f"Proposed action: {tool_name}",
                    payload=payload,
                )
                self._repository.append_event(
                    run_id=run_id,
                    session_id=session_id,
                    event_type="proposed_action.created",
                    visible_title="Proposed action created",
                    visible_summary=f"{tool_name} was converted to a proposed action.",
                    payload={"proposedActionId": proposed_action["id"], "approvalId": approval["id"]},
                )
            response_payload = {
                "finalAnswer": "Approval is required before this action can continue.",
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
            visible_title="Tool started",
            visible_summary=f"{tool_name} started.",
            payload={"toolName": tool_name, "input": payload},
        )
        started = perf_counter()
        dispatch_payload = payload | {"message": str(payload.get("message") or message)}
        if tool_name == "echo_context":
            dispatch_payload = dispatch_payload | {"context": {"sessionId": session_id}}
        tool_result = self._tools.dispatch(tool_name, dispatch_payload)
        duration_ms = max(0, int((perf_counter() - started) * 1000))
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="tool.call_output",
            visible_title="Tool output",
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
            visible_title="Tool completed",
            visible_summary=f"{tool_name} completed.",
            payload={"toolName": tool_name, "status": tool_result.status},
            tool_call_id=int(tool_call["id"]),
        )
        final_answer = f"Echo result: {tool_result.output.get('echo', '')}"
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
            visible_title="Run completed",
            visible_summary="The assistant run completed.",
            payload={"finalAnswer": final_answer},
        )
        return HarnessTurnResult(
            run=completed,
            replayed=False,
            final_answer=final_answer,
            tool_calls=[_tool_call_payload(tool_call)],
        )

    def get_run(self, run_id: int) -> dict[str, Any] | None:
        return self._repository.get_run(run_id)

    def list_session_runs(self, session_id: int) -> list[dict[str, Any]]:
        return self._repository.list_session_runs(session_id)

    def list_run_events(self, run_id: int) -> list[dict[str, Any]]:
        return self._repository.list_run_events(run_id)

    def list_run_tool_calls(self, run_id: int) -> list[dict[str, Any]]:
        return self._repository.list_run_tool_calls(run_id)

    def get_run_inspector(self, run_id: int) -> dict[str, Any] | None:
        run = self._repository.get_run(run_id)
        if run is None:
            return None
        events = self._repository.list_run_events(run_id)
        approvals = self._repository.list_run_approvals(run_id)
        tool_calls = self._repository.list_run_tool_calls(run_id)
        return {
            "run": _run_payload(run),
            "activeTasks": [_task_payload(run, events, approvals)],
            "toolCalls": [_tool_call_payload(row) for row in tool_calls],
            "approvalQueue": [_approval_payload(row) for row in approvals],
            "recentErrors": [_event_timeline_payload(row) for row in _recent_error_events(events)],
            "eventTimeline": [_event_timeline_payload(row) for row in events],
            "usage": _usage_payload(run),
        }

    def list_tool_manifests(self) -> list[dict[str, Any]]:
        return [_manifest_payload(manifest) for manifest in self._tools.list_manifests()]

    def list_pending_approvals(self) -> list[dict[str, Any]]:
        return [_approval_payload(row) for row in self._repository.list_pending_approvals()]

    def approve(self, approval_id: int, actor_id: str) -> dict[str, Any]:
        approval = self._repository.decide_approval(approval_id, "APPROVED", actor_id)
        self._repository.append_event(
            run_id=int(approval["run_id"]),
            session_id=int(approval["session_id"]),
            event_type="approval.granted",
            visible_title="Approval granted",
            visible_summary=f"{actor_id} approved {approval['tool_name']}.",
            payload={"approvalId": approval_id, "actorId": actor_id},
        )
        return _approval_payload(approval)

    def deny(self, approval_id: int, actor_id: str, reason: str = "") -> dict[str, Any]:
        approval = self._repository.decide_approval(approval_id, "DENIED", actor_id, reason)
        self._repository.append_event(
            run_id=int(approval["run_id"]),
            session_id=int(approval["session_id"]),
            event_type="approval.denied",
            visible_title="Approval denied",
            visible_summary=f"{actor_id} denied {approval['tool_name']}.",
            payload={"approvalId": approval_id, "actorId": actor_id, "reason": reason},
            status="DENIED",
        )
        return _approval_payload(approval)


def _request_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return sha256(encoded.encode("utf-8")).hexdigest()


def _tool_call_payload(tool_call: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": tool_call["id"],
        "toolName": tool_call["tool_name"],
        "input": tool_call.get("input_payload") or {},
        "output": tool_call.get("output_payload") or {},
        "status": tool_call["status"],
        "durationMs": tool_call["duration_ms"],
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
    message = str((run.get("input_payload") or {}).get("message") or "Assistant run")
    title = message if len(message) <= 80 else f"{message[:77]}..."
    phase = "waiting_approval" if pending_approval else str((last_event or {}).get("type") or "created")
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
