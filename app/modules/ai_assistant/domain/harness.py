from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from time import perf_counter
from typing import Any

from app.modules.ai_assistant.domain.prompt import PromptAssembler
from app.modules.ai_assistant.domain.tools import ToolRegistry
from app.modules.ai_assistant.infra.repository import AiAssistantRepository, IdempotencyConflict


@dataclass(frozen=True)
class HarnessTurnResult:
    run: dict[str, Any]
    replayed: bool
    final_answer: str
    tool_calls: list[dict[str, Any]]


class AiAssistantHarnessService:
    def __init__(
        self,
        repository: AiAssistantRepository,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        self._repository = repository
        self._tools = tool_registry or ToolRegistry.with_builtin_tools()

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
    ) -> HarnessTurnResult:
        request_hash = _request_hash(message)
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
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="tool.call_started",
            visible_title="Tool started",
            visible_summary="echo_context started.",
            payload={"toolName": "echo_context", "input": {"message": message}},
        )
        started = perf_counter()
        tool_result = self._tools.dispatch("echo_context", {"message": message, "context": {"sessionId": session_id}})
        duration_ms = max(0, int((perf_counter() - started) * 1000))
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="tool.call_output",
            visible_title="Tool output",
            visible_summary=str(tool_result.output.get("echo") or ""),
            payload={"toolName": "echo_context", "output": tool_result.output},
        )
        tool_call = self._repository.record_tool_call(
            run_id=run_id,
            session_id=session_id,
            tool_name="echo_context",
            input_payload={"message": message},
            output_payload=tool_result.output,
            status=tool_result.status,
            duration_ms=duration_ms,
        )
        self._repository.append_event(
            run_id=run_id,
            session_id=session_id,
            event_type="tool.call_completed",
            visible_title="Tool completed",
            visible_summary="echo_context completed.",
            payload={"toolName": "echo_context", "status": tool_result.status},
            tool_call_id=int(tool_call["id"]),
        )
        final_answer = f"Echo result: {tool_result.output['echo']}"
        self._repository.append_message(session_id, "assistant", final_answer, run_id=run_id)
        response_payload = {
            "finalAnswer": final_answer,
            "toolCalls": [_tool_call_payload(tool_call)],
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

    def list_run_events(self, run_id: int) -> list[dict[str, Any]]:
        return self._repository.list_run_events(run_id)

    def list_run_tool_calls(self, run_id: int) -> list[dict[str, Any]]:
        return self._repository.list_run_tool_calls(run_id)

    def list_tool_manifests(self) -> list[dict[str, Any]]:
        return [_manifest_payload(manifest) for manifest in self._tools.list_manifests()]


def _request_hash(message: str) -> str:
    return sha256(message.encode("utf-8")).hexdigest()


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
