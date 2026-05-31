from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Protocol

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
    ) -> list[ToolExecutionResult]:
        results: list[ToolExecutionResult] = []
        for call in calls:
            result = mcp_facade.execute_tool_call(tool_ids, call.name, call.arguments)
            execution_result = self._execution_result(call, result)
            self._audit(call, result, execution_result)
            results.append(execution_result)
        return results

    def _execution_result(self, call: ToolCall, result: McpCallResult) -> ToolExecutionResult:
        if result.elapsed_ms > self._max_elapsed_ms:
            return ToolExecutionResult(
                call_id=call.id,
                name=call.name,
                content="",
                success=False,
                error_message=f"Tool call timed out: {call.name}",
            )
        if result.success:
            return ToolExecutionResult(
                call_id=call.id,
                name=call.name,
                content=result.result or "",
                success=True,
            )
        return ToolExecutionResult(
            call_id=call.id,
            name=call.name,
            content="",
            success=False,
            error_message=result.error_message or "Tool call failed",
        )

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
