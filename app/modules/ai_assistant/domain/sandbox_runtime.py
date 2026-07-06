from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
import re
import shlex
from typing import Any

from app.modules.ai_assistant.domain.sandbox import SandboxDecision, SandboxVerdict


@dataclass(frozen=True)
class SessionSandboxConfig:
    workspace_root: Path
    run_temp_root: Path
    cwd: Path
    env_allowlist: list[str] = field(default_factory=list)
    secret_values: list[str] = field(default_factory=list)
    network_policy: str = "allow"
    resource_limits: dict[str, Any] = field(default_factory=dict)
    allowed_executables: list[str] = field(default_factory=lambda: ["node"])


@dataclass(frozen=True)
class SessionSandboxDecision:
    verdict: str
    reason: str
    evidence: dict[str, Any]
    effective_env: dict[str, str]
    event: dict[str, Any]


class SessionSandboxRuntime:
    def __init__(self, config: SessionSandboxConfig) -> None:
        self.config = config

    @classmethod
    def from_context(
        cls,
        context: dict[str, Any] | None,
        *,
        session_id: int,
        run_id: int,
    ) -> SessionSandboxRuntime:
        workspace_root = Path(os.getenv("HIFY_WORKSPACE_ROOT") or Path.cwd()).resolve()
        raw_workspace = (context or {}).get("aiAssistantWorkspace")
        if isinstance(raw_workspace, dict):
            raw_root = raw_workspace.get("root") or raw_workspace.get("workspaceRoot")
            if isinstance(raw_root, str) and raw_root.strip():
                workspace_root = Path(raw_root).expanduser().resolve()
        raw_sandbox = (context or {}).get("aiAssistantSandbox")
        sandbox = raw_sandbox if isinstance(raw_sandbox, dict) else {}
        cwd = _safe_child_path(workspace_root, sandbox.get("cwd")) or workspace_root
        run_temp_root = (
            _safe_child_path(workspace_root, sandbox.get("runTempRoot"))
            or workspace_root / ".ai-assistant" / "runs" / str(run_id) / "tmp"
        )
        return cls(
            SessionSandboxConfig(
                workspace_root=workspace_root,
                run_temp_root=run_temp_root,
                cwd=cwd,
                env_allowlist=[str(item) for item in sandbox.get("envAllowlist") or []],
                secret_values=[str(item) for item in sandbox.get("secretValues") or [] if str(item)],
                network_policy=str(sandbox.get("networkPolicy") or "allow"),
                resource_limits=dict(sandbox.get("resourceLimits") or {}),
                allowed_executables=[str(item) for item in sandbox.get("allowedExecutables") or ["node"]],
            )
        )

    def evaluate(
        self,
        *,
        session_id: int,
        run_id: int,
        tool_name: str,
        tool_input: dict[str, Any],
        env: dict[str, str] | None = None,
    ) -> SessionSandboxDecision:
        verdict = "allow"
        reason = "sandbox policy allowed tool"
        evidence: dict[str, Any] = {"toolName": tool_name}
        if tool_name == "run_shell":
            verdict, reason, evidence = self._evaluate_shell(tool_input)
        elif tool_name in {
            "read_workspace_file",
            "list_workspace_files",
            "search_workspace_files",
            "edit_workspace_file",
            "write_workspace_file",
            "apply_workspace_patch",
            "propose_agents_update",
        }:
            verdict, reason, evidence = self._evaluate_workspace_path(tool_name, tool_input)
        effective_env = {key: value for key, value in (env or {}).items() if key in set(self.config.env_allowlist)}
        payload = {
            "sessionId": session_id,
            "runId": run_id,
            "toolName": tool_name,
            "verdict": verdict,
            "reason": reason,
            "cwd": str(self.config.cwd),
            "workspaceRoot": str(self.config.workspace_root),
            "runTempRoot": str(self.config.run_temp_root),
            "allowedExecutables": list(self.config.allowed_executables),
            "networkPolicy": self.config.network_policy,
            "redactionApplied": False,
        }
        return SessionSandboxDecision(
            verdict=verdict,
            reason=reason,
            evidence=evidence | payload,
            effective_env=effective_env,
            event={"type": "sandbox.evaluated", "payload": payload},
        )

    def execution_context(self, env: dict[str, str] | None = None) -> dict[str, Any]:
        allowed = set(self.config.env_allowlist)
        effective_env = {key: value for key, value in (env or {}).items() if key in allowed}
        return {
            "cwd": str(self.config.cwd),
            "workspaceRoot": str(self.config.workspace_root),
            "runTempRoot": str(self.config.run_temp_root),
            "env": effective_env,
            "resourceLimits": dict(self.config.resource_limits),
            "secretValues": list(self.config.secret_values),
            "networkPolicy": self.config.network_policy,
            "allowedExecutables": list(self.config.allowed_executables),
        }

    def to_legacy_decision(self, decision: SessionSandboxDecision) -> SandboxDecision:
        verdict = SandboxVerdict.ALLOW if decision.verdict == "allow" else SandboxVerdict.DENY
        return SandboxDecision(verdict=verdict, reason=decision.reason, evidence=decision.evidence)

    def redact_text(self, text: str) -> str:
        redacted = text
        for secret in self.config.secret_values:
            if secret:
                redacted = redacted.replace(secret, "[REDACTED]")
        for pattern in (r"sk-[A-Za-z0-9_-]{8,}", r"Bearer\s+[A-Za-z0-9._-]{8,}"):
            redacted = re.sub(pattern, "[REDACTED]", redacted)
        return redacted

    def redact_payload(self, payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        redacted = _redact_value(payload, self.redact_text)
        return redacted, redacted != payload

    def _evaluate_shell(self, tool_input: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
        command = str(tool_input.get("command") or "").strip()
        evidence = {"toolName": "run_shell", "command": command}
        if not command:
            return "deny", "command is required", evidence
        try:
            argv = shlex.split(command)
        except ValueError as exc:
            return "deny", f"command parse failed: {exc}", evidence
        if not argv:
            return "deny", "command is required", evidence
        executable = Path(argv[0]).name
        evidence["executable"] = executable
        if executable not in set(self.config.allowed_executables):
            return "deny", f"shell executable {executable} is not allowed", evidence
        if any(token in {"&&", "||", "|", ";", ">", ">>", "<", "<<", "&"} for token in argv):
            return "deny", "shell operator is not allowed in controlled commands", evidence
        if executable == "node":
            blocked_flags = {
                "-e",
                "--eval",
                "-p",
                "--print",
                "-r",
                "--require",
                "--import",
                "--loader",
            }
            for token in argv[1:]:
                if (
                    token in blocked_flags
                    or token.startswith("--eval=")
                    or token.startswith("--print=")
                    or token.startswith("--require=")
                    or token.startswith("--import=")
                    or token.startswith("--loader=")
                ):
                    return "deny", "node eval/print/preload flags are not allowed", evidence
            script = _first_node_script_arg(argv)
            if script is None:
                return "deny", "node command must target a workspace script", evidence
            path_decision = self._workspace_path(script)
            if path_decision is not None:
                return path_decision[0], path_decision[1], evidence | path_decision[2]
        return "allow", "controlled command has passed sandbox checks", evidence

    def _evaluate_workspace_path(self, tool_name: str, tool_input: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
        raw_path = str(tool_input.get("path") or "").strip()
        if not raw_path and tool_name in {"list_workspace_files", "search_workspace_files"}:
            raw_path = "."
        if not raw_path:
            return "deny", "path is required", {"toolName": tool_name, "path": raw_path}
        path_decision = self._workspace_path(raw_path)
        if path_decision is not None:
            verdict, reason, evidence = path_decision
            return verdict, reason, {"toolName": tool_name, **evidence}
        return "allow", "workspace path has passed sandbox checks", {"toolName": tool_name, "path": raw_path}

    def _workspace_path(self, raw_path: str) -> tuple[str, str, dict[str, Any]] | None:
        workspace_root = self.config.workspace_root.resolve()
        candidate = (workspace_root / raw_path).resolve()
        try:
            candidate.relative_to(workspace_root)
        except ValueError:
            return "deny", "path must stay inside session workspace", {"path": raw_path}
        return None


def _safe_child_path(root: Path, raw_path: Any) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None
    candidate = Path(raw_path.strip()).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError:
        return None
    return candidate.resolve()


def _first_node_script_arg(argv: list[str]) -> str | None:
    skip_next = False
    value_flags = {"--require", "-r", "--loader", "--import"}
    for token in argv[1:]:
        if skip_next:
            skip_next = False
            continue
        if token in value_flags:
            skip_next = True
            continue
        if token == "--" or token.startswith("-"):
            continue
        return token
    return None


def _redact_value(value: Any, redact_text: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {key: _redact_value(item, redact_text) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_value(item, redact_text) for item in value]
    return value
