from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
import json
from threading import Lock
from typing import Any, Protocol

from app.modules.mcp.domain.client import McpCallResult
from app.modules.provider.infra.llm_adapters import ToolCall

DEFAULT_TOOL_TIMEOUT_MS = 30_000


@dataclass(frozen=True)
class ToolExecutionResult:
    call_id: str
    name: str
    content: str
    success: bool
    error_message: str = ""
    arguments: dict[str, object] = field(default_factory=dict)
    latency_ms: int = 0


@dataclass(frozen=True)
class ToolAuditRecord:
    call_id: str
    tool_name: str
    success: bool
    elapsed_ms: int
    error_message: str = ""


_tool_audit_log: list[ToolAuditRecord] = []
_tool_audit_lock = Lock()


def list_tool_audit_log() -> list[ToolAuditRecord]:
    with _tool_audit_lock:
        return list(_tool_audit_log)


def clear_tool_audit_log() -> None:
    with _tool_audit_lock:
        _tool_audit_log.clear()


class McpToolExecutor(Protocol):
    def execute_tool_call(
        self,
        server_ids: list[int],
        tool_name: str,
        arguments: dict[str, object],
    ) -> McpCallResult:
        ...


class ToolCallRunner:
    def __init__(self, max_elapsed_ms: int = DEFAULT_TOOL_TIMEOUT_MS) -> None:
        if max_elapsed_ms <= 0:
            raise ValueError("max_elapsed_ms must be greater than 0")
        self._max_elapsed_ms = max_elapsed_ms

    def run(
        self,
        tool_ids: list[int],
        content: str,
        tool_names: list[str] | None = None,
    ) -> str | None:
        if not tool_ids:
            return None
        if "tool" not in content.lower():
            return None
        if tool_names:
            return f"Tool mock ({', '.join(tool_names)}): {content}"
        return f"Tool mock: {content}"

    def run_calls(
        self,
        tool_ids: list[int],
        calls: list[ToolCall],
        mcp_facade: McpToolExecutor,
        tool_policies: dict[str, dict[str, Any]] | None = None,
    ) -> list[ToolExecutionResult]:
        results: list[ToolExecutionResult] = []
        for call in calls:
            policy = (tool_policies or {}).get(call.name, {})
            if policy.get("enabled") is False:
                execution_result = ToolExecutionResult(
                    call_id=call.id,
                    name=call.name,
                    content="",
                    success=False,
                    error_message=f"Tool disabled by policy: {call.name}",
                    arguments=dict(call.arguments),
                    latency_ms=0,
                )
                results.append(execution_result)
                continue
            arguments = self._arguments_with_presets(call.arguments, policy)
            result = mcp_facade.execute_tool_call(tool_ids, call.name, arguments)
            execution_result = self._execution_result(call, result, policy, arguments)
            self._audit(call, result, execution_result)
            results.append(execution_result)
        return results

    def _execution_result(
        self,
        call: ToolCall,
        result: McpCallResult,
        policy: dict[str, Any] | None = None,
        arguments: dict[str, object] | None = None,
    ) -> ToolExecutionResult:
        final_arguments = dict(arguments or call.arguments)
        timeout_ms = self._timeout_ms(policy)
        if result.elapsed_ms > timeout_ms:
            return ToolExecutionResult(
                call_id=call.id,
                name=call.name,
                content="",
                success=False,
                error_message=f"Tool call timed out: {call.name}",
                arguments=final_arguments,
                latency_ms=result.elapsed_ms,
            )
        if result.success:
            return ToolExecutionResult(
                call_id=call.id,
                name=call.name,
                content=result.result or "",
                success=True,
                arguments=final_arguments,
                latency_ms=result.elapsed_ms,
            )
        return ToolExecutionResult(
            call_id=call.id,
            name=call.name,
            content="",
            success=False,
            error_message=result.error_message or "Tool call failed",
            arguments=final_arguments,
            latency_ms=result.elapsed_ms,
        )

    def _arguments_with_presets(self, arguments: dict[str, object], policy: dict[str, Any]) -> dict[str, object]:
        presets = policy.get("argumentPresets")
        if not isinstance(presets, dict):
            return dict(arguments)
        return {**arguments, **presets}

    def _timeout_ms(self, policy: dict[str, Any] | None) -> int:
        if not policy:
            return self._max_elapsed_ms
        try:
            timeout = int(policy.get("timeoutMs") or self._max_elapsed_ms)
        except (TypeError, ValueError):
            return self._max_elapsed_ms
        return timeout if timeout > 0 else self._max_elapsed_ms

    def _audit(
        self,
        call: ToolCall,
        result: McpCallResult,
        execution_result: ToolExecutionResult,
    ) -> None:
        with _tool_audit_lock:
            _tool_audit_log.append(
                ToolAuditRecord(
                    call_id=call.id,
                    tool_name=call.name,
                    success=execution_result.success,
                    elapsed_ms=result.elapsed_ms,
                    error_message=execution_result.error_message,
                )
            )


def normalize_tool_execution_results(results: list[ToolExecutionResult]) -> list[dict[str, Any]]:
    return [
        {
            "callId": result.call_id,
            "toolName": result.name,
            "arguments": dict(result.arguments),
            "argumentsSummary": _summary(result.arguments),
            "latencyMs": int(result.latency_ms),
            "status": "success" if result.success else "failed",
            "contentSummary": _summary(result.content) if result.success else "",
            "errorMessage": result.error_message,
        }
        for result in results
    ]


def _summary(value: Any, limit: int = 240) -> str:
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, sort_keys=True)
        except TypeError:
            text = str(value)
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."
