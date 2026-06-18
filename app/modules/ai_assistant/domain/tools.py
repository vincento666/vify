from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import os
from pathlib import Path
from typing import Any, Callable

from app.modules.customer_assistant.harness_adapter import (
    event_stream_ref,
    reserved_worker_async_refs,
    result_ref,
    sub_agent_run_public_id,
    unsupported_cancellation,
)


class RiskLevel(StrEnum):
    READ = "READ"
    LOW_WRITE = "LOW_WRITE"
    BUSINESS_WRITE = "BUSINESS_WRITE"
    DESTRUCTIVE = "DESTRUCTIVE"
    EXTERNAL_SIDE_EFFECT = "EXTERNAL_SIDE_EFFECT"


@dataclass(frozen=True)
class ToolManifest:
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    timeout_ms: int
    risk_level: RiskLevel
    read_resources: list[str]
    write_resources: list[str]
    policy_ref: str


@dataclass(frozen=True)
class ToolResult:
    status: str
    output: dict[str, Any]


ToolHandler = Callable[[dict[str, Any]], ToolResult]


class ToolRegistry:
    def __init__(self, tools: dict[str, tuple[ToolManifest, ToolHandler]]) -> None:
        self._tools = tools

    @classmethod
    def with_builtin_tools(cls) -> ToolRegistry:
        echo_manifest = ToolManifest(
            name="echo_context",
            description="回显当前用户消息和安全上下文，用于助手运行验证。",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "context": {"type": "object"},
                },
                "required": ["message"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "echo": {"type": "string"},
                    "context": {"type": "object"},
                },
                "required": ["echo", "context"],
            },
            timeout_ms=1000,
            risk_level=RiskLevel.READ,
            read_resources=["session:{session_id}"],
            write_resources=[],
            policy_ref="ai_assistant_read_only",
        )
        business_write_manifest = ToolManifest(
            name="update_customer_profile",
            description="把客户资料修改请求转换为需要审批的高风险拟执行动作。",
            input_schema={
                "type": "object",
                "properties": {
                    "customerId": {"type": "string"},
                    "field": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["customerId"],
            },
            output_schema={"type": "object", "properties": {"status": {"type": "string"}}},
            timeout_ms=1000,
            risk_level=RiskLevel.BUSINESS_WRITE,
            read_resources=[],
            write_resources=["customer:{customerId}"],
            policy_ref="ai_assistant_business_write_requires_approval",
        )
        shell_manifest = ToolManifest(
            name="run_shell",
            description="类 Shell 执行占位工具，默认被沙箱策略阻断。",
            input_schema={
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
            output_schema={"type": "object"},
            timeout_ms=1000,
            risk_level=RiskLevel.EXTERNAL_SIDE_EFFECT,
            read_resources=[],
            write_resources=["external:shell"],
            policy_ref="ai_assistant_shell_blocked",
        )
        customer_bridge_manifest = ToolManifest(
            name="customer_assistant_subagent_bridge",
            description="读取客服助手子任务引用，供 AI 助手检查任务状态。",
            input_schema={
                "type": "object",
                "properties": {
                    "sessionId": {"type": "integer"},
                    "runId": {"type": "integer"},
                    "message": {"type": "string"},
                },
                "required": ["sessionId", "runId"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "agentType": {"type": "string"},
                    "subAgentRunId": {"type": "string"},
                    "eventStreamRef": {"type": "string"},
                    "resultRef": {"type": "string"},
                    "workerAsyncRefs": {"type": "object"},
                    "cancellation": {"type": "object"},
                },
                "required": ["agentType", "subAgentRunId", "eventStreamRef", "resultRef"],
            },
            timeout_ms=1000,
            risk_level=RiskLevel.READ,
            read_resources=["customer_assistant:session:{sessionId}", "customer_assistant:run:{runId}"],
            write_resources=[],
            policy_ref="ai_assistant_customer_assistant_bridge_read_only",
        )
        return cls(
            {
                "echo_context": (echo_manifest, _echo_context),
                "update_customer_profile": (business_write_manifest, _blocked_write),
                "run_shell": (shell_manifest, _blocked_write),
                "customer_assistant_subagent_bridge": (customer_bridge_manifest, _customer_assistant_bridge),
                "read_workspace_file": (_read_file_manifest(), _read_workspace_file),
                "write_workspace_file": (_write_file_manifest(), _write_workspace_file),
                "invoke_skill": (_skill_manifest(), _invoke_skill),
                "search_knowledge_base": (_knowledge_base_manifest(), _search_knowledge_base),
            }
        )

    def get_manifest(self, name: str) -> ToolManifest:
        try:
            return self._tools[name][0]
        except KeyError as exc:
            raise KeyError(f"Unknown AI Assistant tool: {name}") from exc

    def list_manifests(self) -> list[ToolManifest]:
        return [entry[0] for entry in self._tools.values()]

    def dispatch(self, name: str, payload: dict[str, Any]) -> ToolResult:
        try:
            handler = self._tools[name][1]
        except KeyError as exc:
            raise KeyError(f"Unknown AI Assistant tool: {name}") from exc
        return handler(payload)


def _echo_context(payload: dict[str, Any]) -> ToolResult:
    return ToolResult(
        status="COMPLETED",
        output={
            "echo": str(payload.get("message") or ""),
            "context": dict(payload.get("context") or {}),
        },
    )


def _blocked_write(_payload: dict[str, Any]) -> ToolResult:
    return ToolResult(status="BLOCKED", output={"status": "BLOCKED"})


def _customer_assistant_bridge(payload: dict[str, Any]) -> ToolResult:
    session_id = int(payload.get("sessionId") or 0)
    run_id = int(payload.get("runId") or 0)
    return ToolResult(
        status="COMPLETED",
        output={
            "agentType": "customer_assistant",
            "status": "linked",
            "sessionId": session_id,
            "runId": run_id,
            "subAgentRunId": sub_agent_run_public_id(run_id),
            "eventStreamRef": event_stream_ref(session_id),
            "resultRef": result_ref(run_id),
            "workerAsyncRefs": reserved_worker_async_refs(run_id=run_id, session_id=session_id),
            "cancellation": unsupported_cancellation(),
            "message": str(payload.get("message") or ""),
        },
    )


def _read_file_manifest() -> ToolManifest:
    return ToolManifest(
        name="read_workspace_file",
        description="读取工作区内的文本文件，并返回截断预览。",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
                "truncated": {"type": "boolean"},
            },
        },
        timeout_ms=2000,
        risk_level=RiskLevel.READ,
        read_resources=["file:{path}"],
        write_resources=[],
        policy_ref="ai_assistant_workspace_file_read",
    )


def _write_file_manifest() -> ToolManifest:
    return ToolManifest(
        name="write_workspace_file",
        description="写入工作区文本文件；该工具必须经过审批才能执行。",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
        output_schema={"type": "object", "properties": {"path": {"type": "string"}, "bytes": {"type": "integer"}}},
        timeout_ms=2000,
        risk_level=RiskLevel.BUSINESS_WRITE,
        read_resources=[],
        write_resources=["file:{path}"],
        policy_ref="ai_assistant_workspace_file_write_requires_approval",
    )


def _skill_manifest() -> ToolManifest:
    return ToolManifest(
        name="invoke_skill",
        description="记录一次技能调用意图，并返回技能名与调用说明。",
        input_schema={
            "type": "object",
            "properties": {
                "skillName": {"type": "string"},
                "instruction": {"type": "string"},
            },
            "required": ["skillName"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "skillName": {"type": "string"},
                "instruction": {"type": "string"},
                "status": {"type": "string"},
            },
        },
        timeout_ms=1000,
        risk_level=RiskLevel.READ,
        read_resources=["skill:{skillName}"],
        write_resources=[],
        policy_ref="ai_assistant_skill_invocation_read_only",
    )


def _knowledge_base_manifest() -> ToolManifest:
    return ToolManifest(
        name="search_knowledge_base",
        description="检索系统内知识库，返回可回放的只读查询结果摘要。",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "knowledgeBaseId": {"type": "integer"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": ["query"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "knowledgeBaseId": {"type": ["integer", "null"]},
                "limit": {"type": "integer"},
                "source": {"type": "string"},
                "hits": {"type": "array"},
            },
            "required": ["query", "limit", "source", "hits"],
        },
        timeout_ms=1500,
        risk_level=RiskLevel.READ,
        read_resources=["knowledge_base", "knowledge_base:{knowledgeBaseId}", "knowledge_base:search"],
        write_resources=[],
        policy_ref="ai_assistant_knowledge_base_search_read_only",
    )


def _read_workspace_file(payload: dict[str, Any]) -> ToolResult:
    path = _safe_workspace_path(payload)
    if not path.exists() or not path.is_file():
        return ToolResult(
            status="NOT_FOUND",
            output={"path": str(path.relative_to(_workspace_root())), "content": "", "truncated": False},
        )
    content = path.read_text(encoding="utf-8")
    truncated = len(content) > 12000
    return ToolResult(
        status="COMPLETED",
        output={"path": str(path.relative_to(_workspace_root())), "content": content[:12000], "truncated": truncated},
    )


def _write_workspace_file(payload: dict[str, Any]) -> ToolResult:
    path = _safe_workspace_path(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = str(payload.get("content") or "")
    path.write_text(content, encoding="utf-8")
    return ToolResult(status="COMPLETED", output={"path": str(path.relative_to(_workspace_root())), "bytes": len(content)})


def _invoke_skill(payload: dict[str, Any]) -> ToolResult:
    return ToolResult(
        status="COMPLETED",
        output={
            "skillName": str(payload.get("skillName") or ""),
            "instruction": str(payload.get("instruction") or ""),
            "status": "RECORDED",
        },
    )


def _search_knowledge_base(payload: dict[str, Any]) -> ToolResult:
    query = str(payload.get("query") or "").strip()
    knowledge_base_id = _optional_int(payload.get("knowledgeBaseId"))
    limit = max(1, min(_optional_int(payload.get("limit")) or 5, 10))
    raw_hits = payload.get("hits")
    hits = raw_hits[:limit] if isinstance(raw_hits, list) else []
    return ToolResult(
        status="COMPLETED",
        output={
            "query": query,
            "knowledgeBaseId": knowledge_base_id,
            "limit": limit,
            "source": "system_knowledge_base",
            "hits": hits,
            "warning": "当前 Harness 记录了知识库检索调用；未绑定具体知识库索引时返回空命中。",
        },
    )


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_workspace_path(payload: dict[str, Any]) -> Path:
    raw = str(payload.get("path") or "").strip()
    if not raw:
        raise ValueError("path is required")
    root = _workspace_root()
    candidate = (root / raw).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("path must stay inside workspace")
    return candidate


def _workspace_root() -> Path:
    return Path(os.getenv("HIFY_WORKSPACE_ROOT") or Path.cwd()).resolve()
