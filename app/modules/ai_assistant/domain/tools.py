from __future__ import annotations

from dataclasses import dataclass
import difflib
from enum import StrEnum
import os
from pathlib import Path
import shlex
import shutil
import subprocess
from time import perf_counter
from typing import Any, Callable

from app.modules.ai_assistant.domain import file_workspace
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
        tools: dict[str, tuple[ToolManifest, ToolHandler]] = {
            "echo_context": (echo_manifest, _echo_context),
            "update_customer_profile": (business_write_manifest, _blocked_write),
            "run_shell": (shell_manifest, _run_shell),
            "customer_assistant_subagent_bridge": (customer_bridge_manifest, _customer_assistant_bridge),
            "read_workspace_file": (_read_file_manifest(), _read_workspace_file),
            "list_workspace_files": (_list_files_manifest(), _list_workspace_files),
            "search_workspace_files": (_search_files_manifest(), _search_workspace_files),
            "edit_workspace_file": (_edit_file_manifest(), _edit_workspace_file),
            "write_workspace_file": (_write_file_manifest(), _write_workspace_file),
            "apply_workspace_patch": (_apply_patch_manifest(), _apply_workspace_patch),
            "propose_agents_update": (_propose_agents_update_manifest(), _propose_agents_update),
            "invoke_skill": (_skill_manifest(), _invoke_skill),
            "read_skill_resource": (_read_skill_resource_manifest(), _read_skill_resource),
            "run_skill_script": (_run_skill_script_manifest(), _run_skill_script),
            "search_knowledge_base": (_knowledge_base_manifest(), _search_knowledge_base),
        }
        from app.modules.ai_assistant.domain.business_adapter import (  # noqa: PLC0415
            MockAviationAdapter,
            tool_entries_for_business_adapter,
        )

        tools.update(tool_entries_for_business_adapter(MockAviationAdapter()))
        return cls(tools)

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
                "checksum": {"type": "string"},
                "mtimeNs": {"type": "integer"},
                "sizeBytes": {"type": "integer"},
            },
        },
        timeout_ms=2000,
        risk_level=RiskLevel.READ,
        read_resources=["file:{path}"],
        write_resources=[],
        policy_ref="ai_assistant_workspace_file_read",
    )


def _list_files_manifest() -> ToolManifest:
    return ToolManifest(
        name="list_workspace_files",
        description="列出工作区内的文件，并返回路径和文件元数据。",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "pattern": {"type": "string"},
                "limit": {"type": "integer"},
            },
        },
        output_schema={"type": "object"},
        timeout_ms=2000,
        risk_level=RiskLevel.READ,
        read_resources=["file:{path}"],
        write_resources=[],
        policy_ref="ai_assistant_workspace_file_read",
    )


def _search_files_manifest() -> ToolManifest:
    return ToolManifest(
        name="search_workspace_files",
        description="搜索工作区文本文件内容，并返回匹配行。",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "query": {"type": "string"},
                "pattern": {"type": "string"},
                "limit": {"type": "integer"},
                "caseSensitive": {"type": "boolean"},
            },
            "required": ["query"],
        },
        output_schema={"type": "object"},
        timeout_ms=2000,
        risk_level=RiskLevel.READ,
        read_resources=["file:{path}"],
        write_resources=[],
        policy_ref="ai_assistant_workspace_file_read",
    )


def _edit_file_manifest() -> ToolManifest:
    return ToolManifest(
        name="edit_workspace_file",
        description="对工作区文本文件执行唯一匹配编辑，支持预览、前置条件、快照和原子写入。",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "oldText": {"type": "string"},
                "newText": {"type": "string"},
                "beforeContext": {"type": "string"},
                "afterContext": {"type": "string"},
                "whitespaceTolerant": {"type": "boolean"},
                "expectedChecksum": {"type": "string"},
                "expectedMtimeNs": {"type": "integer"},
                "dryRun": {"type": "boolean"},
            },
            "required": ["path", "oldText", "newText"],
        },
        output_schema={"type": "object"},
        timeout_ms=2000,
        risk_level=RiskLevel.BUSINESS_WRITE,
        read_resources=["file:{path}"],
        write_resources=["file:{path}"],
        policy_ref="ai_assistant_workspace_file_write_requires_approval",
    )


def _write_file_manifest() -> ToolManifest:
    return ToolManifest(
        name="write_workspace_file",
        description="安全写入工作区文本文件，支持前置条件、快照和原子写入；该工具必须经过审批才能执行。",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
                "expectedChecksum": {"type": "string"},
                "expectedMtimeNs": {"type": "integer"},
                "dryRun": {"type": "boolean"},
            },
            "required": ["path", "content"],
        },
        output_schema={"type": "object"},
        timeout_ms=2000,
        risk_level=RiskLevel.BUSINESS_WRITE,
        read_resources=["file:{path}"],
        write_resources=["file:{path}"],
        policy_ref="ai_assistant_workspace_file_write_requires_approval",
    )


def _apply_patch_manifest() -> ToolManifest:
    return ToolManifest(
        name="apply_workspace_patch",
        description="按结构化 patch operations 修改工作区文本文件，支持前置条件、预览、快照和原子写入。",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "operations": {"type": "array"},
                "expectedChecksum": {"type": "string"},
                "expectedMtimeNs": {"type": "integer"},
                "dryRun": {"type": "boolean"},
            },
            "required": ["path", "operations"],
        },
        output_schema={"type": "object"},
        timeout_ms=2000,
        risk_level=RiskLevel.BUSINESS_WRITE,
        read_resources=["file:{path}"],
        write_resources=["file:{path}"],
        policy_ref="ai_assistant_workspace_file_write_requires_approval",
    )


def _propose_agents_update_manifest() -> ToolManifest:
    return ToolManifest(
        name="propose_agents_update",
        description="为 AGENTS.md 更新生成审批用 diff 预览；不在未审批前直接写入文件。",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["path", "content", "reason"],
        },
        output_schema={"type": "object"},
        timeout_ms=1000,
        risk_level=RiskLevel.BUSINESS_WRITE,
        read_resources=["file:{path}"],
        write_resources=["file:{path}"],
        policy_ref="ai_assistant_agents_update_requires_approval",
    )


def _skill_manifest() -> ToolManifest:
    return ToolManifest(
        name="invoke_skill",
        description="按需加载一个 Skill 的 SKILL.md，并返回技能内容与可审计 metadata。",
        input_schema={
            "type": "object",
            "properties": {
                "skillName": {"type": "string"},
                "instruction": {"type": "string"},
                "resources": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["skillName"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "skillName": {"type": "string"},
                "instruction": {"type": "string"},
                "status": {"type": "string"},
                "metadata": {"type": "object"},
                "skillMarkdown": {"type": "string"},
                "resources": {"type": "array"},
            },
        },
        timeout_ms=1000,
        risk_level=RiskLevel.READ,
        read_resources=["skill:{skillName}"],
        write_resources=[],
        policy_ref="ai_assistant_skill_invocation_read_only",
    )


def _read_skill_resource_manifest() -> ToolManifest:
    return ToolManifest(
        name="read_skill_resource",
        description="按需读取已发现 Skill 下的 references、scripts 或 assets 资源。",
        input_schema={
            "type": "object",
            "properties": {
                "skillName": {"type": "string"},
                "path": {"type": "string"},
            },
            "required": ["skillName", "path"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "skillName": {"type": "string"},
                "path": {"type": "string"},
                "kind": {"type": "string"},
                "content": {"type": "string"},
                "checksum": {"type": "string"},
            },
        },
        timeout_ms=1000,
        risk_level=RiskLevel.READ,
        read_resources=["skill:{skillName}:{path}"],
        write_resources=[],
        policy_ref="ai_assistant_skill_resource_read_only",
    )


def _run_skill_script_manifest() -> ToolManifest:
    return ToolManifest(
        name="run_skill_script",
        description="规划一次 Skill 脚本调用；必须先通过高风险审批与 ToolRuntime 审计。",
        input_schema={
            "type": "object",
            "properties": {
                "skillName": {"type": "string"},
                "scriptPath": {"type": "string"},
            },
            "required": ["skillName", "scriptPath"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "skillName": {"type": "string"},
                "scriptPath": {"type": "string"},
                "status": {"type": "string"},
                "command": {"type": "string"},
            },
        },
        timeout_ms=1000,
        risk_level=RiskLevel.EXTERNAL_SIDE_EFFECT,
        read_resources=["skill:{skillName}:{scriptPath}"],
        write_resources=["external:skill_script:{skillName}:{scriptPath}"],
        policy_ref="ai_assistant_skill_script_requires_approval",
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
    return _workspace_result(file_workspace.read_workspace_file(payload))


def _list_workspace_files(payload: dict[str, Any]) -> ToolResult:
    return _workspace_result(file_workspace.list_workspace_files(payload))


def _search_workspace_files(payload: dict[str, Any]) -> ToolResult:
    return _workspace_result(file_workspace.search_workspace_files(payload))


def _edit_workspace_file(payload: dict[str, Any]) -> ToolResult:
    return _workspace_result(file_workspace.edit_workspace_file(payload))


def _write_workspace_file(payload: dict[str, Any]) -> ToolResult:
    return _workspace_result(file_workspace.write_workspace_file(payload))


def _apply_workspace_patch(payload: dict[str, Any]) -> ToolResult:
    return _workspace_result(file_workspace.apply_workspace_patch(payload))


def _propose_agents_update(payload: dict[str, Any]) -> ToolResult:
    path = str(payload.get("path") or "AGENTS.md")
    content = str(payload.get("content") or "")
    if not path.endswith("AGENTS.md"):
        return ToolResult(
            status="FAILED",
            output={"error": {"code": "INVALID_AGENTS_PATH", "message": "Only AGENTS.md update proposals are allowed."}},
        )
    current = file_workspace.read_workspace_file({"path": path})
    before = str(current.output.get("content") or "") if current.status == "COMPLETED" else ""
    diff = "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            content.splitlines(keepends=True),
            fromfile=path,
            tofile=path,
        )
    )
    return ToolResult(
        status="COMPLETED",
        output={
            "path": path,
            "reason": str(payload.get("reason") or ""),
            "diffPreview": diff,
            "requiresApproval": True,
            "applied": False,
        },
    )


def _workspace_result(result: file_workspace.WorkspaceOperationResult) -> ToolResult:
    return ToolResult(status=result.status, output=result.output)


def _run_shell(payload: dict[str, Any]) -> ToolResult:
    command = str(payload.get("command") or "").strip()
    if not command:
        return ToolResult(status="FAILED", output={"command": command, "exitCode": 2, "stdout": "", "stderr": "command is required"})
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        return ToolResult(status="FAILED", output={"command": command, "exitCode": 2, "stdout": "", "stderr": str(exc)})
    sandbox = _sandbox_payload(payload)
    argv = _resolve_sandbox_executable(argv)
    started = perf_counter()
    timeout_seconds = _shell_timeout_seconds(payload, sandbox)
    try:
        completed = subprocess.run(  # noqa: S603 - argv is sandbox-validated and shell=False by default.
            argv,
            cwd=_sandbox_cwd(sandbox),
            env=_sandbox_env(sandbox),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError as exc:
        return ToolResult(
            status="FAILED",
            output={
                "command": command,
                "exitCode": 127,
                "stdout": "",
                "stderr": str(exc),
                "durationMs": _duration_ms(started),
            },
        )
    except subprocess.TimeoutExpired as exc:
        return ToolResult(
            status="TIMED_OUT",
            output={
                "command": command,
                "exitCode": 124,
                "stdout": _truncate_output(exc.stdout or ""),
                "stderr": _truncate_output(exc.stderr or "command timed out"),
                "durationMs": _duration_ms(started),
                "timeoutMs": int(timeout_seconds * 1000),
            },
        )
    return ToolResult(
        status="COMPLETED" if completed.returncode == 0 else "FAILED",
        output={
            "command": command,
            "exitCode": completed.returncode,
            "stdout": _truncate_output(completed.stdout),
            "stderr": _truncate_output(completed.stderr),
            "durationMs": _duration_ms(started),
        },
    )


def _invoke_skill(payload: dict[str, Any]) -> ToolResult:
    from app.modules.ai_assistant.domain.skills import SkillRuntimeError

    skill_name = str(payload.get("skillName") or "")
    instruction = str(payload.get("instruction") or "")
    session_id, run_id = _runtime_ids(payload)
    try:
        runtime = _skill_runtime(payload)
        loaded = runtime.load_skill(skill_name, reason=instruction or "invoke_skill", session_id=session_id, run_id=run_id)
        audit_events = list(loaded.audit_events)
        resources = []
        for path in _requested_skill_resources(payload):
            resource = runtime.read_resource(skill_name, path, session_id=session_id, run_id=run_id)
            audit_events.extend(resource.audit_events)
            resources.append(
                {
                    "path": resource.path,
                    "kind": resource.kind,
                    "content": resource.content,
                    "checksum": resource.checksum,
                }
            )
    except SkillRuntimeError as exc:
        return ToolResult(
            status="COMPLETED",
            output={
                "skillName": skill_name,
                "instruction": instruction,
                "status": "UNAVAILABLE",
                "metadata": {"name": skill_name, "contentLoaded": False},
                "skillMarkdown": "",
                "resources": [],
                "warning": str(exc),
            },
        )
    return ToolResult(
        status="COMPLETED",
        output={
            "skillName": loaded.manifest.name,
            "instruction": instruction,
            "status": "LOADED",
            "metadata": _skill_manifest_output(loaded.manifest),
            "skillMarkdown": loaded.content,
            "resources": resources,
            "_auditEvents": audit_events,
        },
    )


def _read_skill_resource(payload: dict[str, Any]) -> ToolResult:
    from app.modules.ai_assistant.domain.skills import SkillRuntimeError

    skill_name = str(payload.get("skillName") or "")
    path = str(payload.get("path") or "")
    session_id, run_id = _runtime_ids(payload)
    try:
        resource = _skill_runtime(payload).read_resource(skill_name, path, session_id=session_id, run_id=run_id)
    except SkillRuntimeError as exc:
        return _skill_error_result("read_skill_resource", payload, skill_name, str(exc))
    return ToolResult(
        status="COMPLETED",
        output={
            "skillName": resource.skill_name,
            "path": resource.path,
            "kind": resource.kind,
            "content": resource.content,
            "checksum": resource.checksum,
            "_auditEvents": resource.audit_events,
        },
    )


def _run_skill_script(payload: dict[str, Any]) -> ToolResult:
    from app.modules.ai_assistant.domain.skills import SkillRuntimeError

    skill_name = str(payload.get("skillName") or "")
    script_path = str(payload.get("scriptPath") or "")
    session_id, run_id = _runtime_ids(payload)
    try:
        invocation = _skill_runtime(payload).plan_script_invocation(skill_name, script_path, session_id=session_id, run_id=run_id)
    except SkillRuntimeError as exc:
        return _skill_error_result("run_skill_script", payload, skill_name, str(exc))
    return ToolResult(
        status="COMPLETED",
        output={
            "skillName": invocation.skill_name,
            "scriptPath": invocation.script_path,
            "status": invocation.status,
            "command": invocation.command,
            "_auditEvents": invocation.audit_events,
        },
    )


def _skill_runtime(payload: dict[str, Any]) -> Any:
    runtime = payload.get("_skillRuntime")
    if runtime is not None and hasattr(runtime, "load_skill") and hasattr(runtime, "read_resource"):
        return runtime
    from app.modules.ai_assistant.domain.skills import SkillRuntime

    return SkillRuntime()


def _runtime_ids(payload: dict[str, Any]) -> tuple[int, int]:
    runtime = payload.get("_aiAssistantRuntime")
    if not isinstance(runtime, dict):
        return 0, 0
    return int(runtime.get("sessionId") or 0), int(runtime.get("runId") or 0)


def _requested_skill_resources(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("resources") or []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(item) for item in raw if str(item).strip()]
    return []


def _skill_manifest_output(manifest: Any) -> dict[str, Any]:
    return {
        "name": str(manifest.name),
        "description": str(manifest.description),
        "path": str(manifest.path),
        "version": str(manifest.version),
        "checksum": str(manifest.checksum),
        "riskLevel": str(manifest.risk_level),
        "contentLoaded": bool(manifest.content_loaded),
        "references": list(manifest.references),
        "scripts": list(manifest.scripts),
        "assets": list(manifest.assets),
    }


def _skill_error_result(tool_name: str, payload: dict[str, Any], skill_name: str, message: str) -> ToolResult:
    public_payload = {key: value for key, value in payload.items() if not str(key).startswith("_")}
    error = {
        "code": "SKILL_RUNTIME_ERROR",
        "message": message,
        "type": "SkillRuntimeError",
        "retriable": False,
    }
    observation = {
        "kind": "tool_error",
        "toolName": tool_name,
        "toolInput": public_payload,
        "idempotencyKey": str((payload.get("_toolRuntime") or {}).get("idempotencyKey") or ""),
        "attempts": int((payload.get("_toolRuntime") or {}).get("attempt") or 0),
        "error": error,
        "retriable": False,
        "modelVisible": True,
        "suggestedActions": ["choose_existing_skill", "read_skill_index", "revise_plan"],
    }
    return ToolResult(
        status="FAILED",
        output={
            "skillName": skill_name,
            "status": "FAILED",
            "message": message,
            "error": error,
            "observation": observation,
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


def _shell_timeout_seconds(payload: dict[str, Any], sandbox: dict[str, Any] | None = None) -> float:
    requested = _optional_int(payload.get("timeoutMs")) or 10000
    limits = dict((sandbox or {}).get("resourceLimits") or {})
    limit_timeout = _optional_int(limits.get("timeoutMs"))
    if limit_timeout is not None:
        requested = min(requested, limit_timeout)
    return max(0.5, min(requested, 30000) / 1000)


def _duration_ms(started: float) -> int:
    return max(1, int((perf_counter() - started) * 1000))


def _truncate_output(output: object) -> str:
    if isinstance(output, bytes):
        text = output.decode("utf-8", errors="replace")
    else:
        text = str(output or "")
    return text[:12000]


def _sandbox_payload(payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get("_sandbox")
    return dict(raw) if isinstance(raw, dict) else {}


def _sandbox_cwd(sandbox: dict[str, Any]) -> Path:
    raw_cwd = sandbox.get("cwd")
    if isinstance(raw_cwd, str) and raw_cwd.strip():
        return Path(raw_cwd).expanduser().resolve()
    return _workspace_root()


def _sandbox_env(sandbox: dict[str, Any]) -> dict[str, str] | None:
    raw_env = sandbox.get("env")
    if not isinstance(raw_env, dict):
        return None
    return {str(key): str(value) for key, value in raw_env.items()}


def _resolve_sandbox_executable(argv: list[str]) -> list[str]:
    if not argv:
        return argv
    executable = argv[0]
    if Path(executable).is_absolute():
        return argv
    resolved = shutil.which(executable)
    if resolved is None:
        return argv
    return [resolved, *argv[1:]]


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
