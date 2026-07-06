from dataclasses import dataclass
from enum import StrEnum
import os
from pathlib import Path
import shlex
from typing import Any


class SandboxVerdict(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"


@dataclass(frozen=True)
class SandboxDecision:
    verdict: SandboxVerdict
    reason: str
    evidence: dict[str, Any]


class SandboxPolicy:
    def evaluate(self, tool_name: str, tool_input: dict[str, Any]) -> SandboxDecision:
        if tool_name == "run_shell":
            return _evaluate_shell_command(tool_name, tool_input)
        if tool_name in {
            "read_workspace_file",
            "list_workspace_files",
            "search_workspace_files",
            "edit_workspace_file",
            "write_workspace_file",
            "apply_workspace_patch",
        }:
            root = Path(os.getenv("HIFY_WORKSPACE_ROOT") or Path.cwd()).resolve()
            raw_path = str(tool_input.get("path") or "").strip()
            if not raw_path and tool_name in {"list_workspace_files", "search_workspace_files"}:
                raw_path = "."
            candidate = (root / raw_path).resolve()
            if not raw_path or (candidate != root and root not in candidate.parents):
                return SandboxDecision(
                    verdict=SandboxVerdict.DENY,
                    reason="文件路径必须位于当前工作区内",
                    evidence={"toolName": tool_name, "path": raw_path},
                )
        return SandboxDecision(
            verdict=SandboxVerdict.ALLOW,
            reason="工具已通过沙箱检查",
            evidence={"toolName": tool_name},
        )


def _evaluate_shell_command(tool_name: str, tool_input: dict[str, Any]) -> SandboxDecision:
    command = str(tool_input.get("command") or "").strip()
    evidence: dict[str, Any] = {"toolName": tool_name, "command": command}
    if not command:
        return SandboxDecision(SandboxVerdict.DENY, "command is required", evidence)
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        return SandboxDecision(SandboxVerdict.DENY, f"command parse failed: {exc}", evidence)
    if not argv:
        return SandboxDecision(SandboxVerdict.DENY, "command is required", evidence)
    if _contains_shell_operator(argv):
        return SandboxDecision(SandboxVerdict.DENY, "shell operator is not allowed in controlled commands", evidence)

    executable = Path(argv[0]).name
    evidence["executable"] = executable
    allowed = _allowed_shell_executables()
    if executable not in allowed:
        return SandboxDecision(
            SandboxVerdict.DENY,
            f"shell executable {executable} is not allowed by the controlled command sandbox",
            evidence | {"allowedExecutables": sorted(allowed)},
        )
    if executable == "node":
        return _evaluate_node_command(argv, evidence)
    return SandboxDecision(
        SandboxVerdict.ALLOW,
        "controlled command has passed sandbox checks",
        evidence,
    )


def _allowed_shell_executables() -> set[str]:
    raw = os.getenv("HIFY_AI_ASSISTANT_ALLOWED_SHELL_EXECUTABLES") or "node"
    return {item.strip() for item in raw.split(",") if item.strip()}


def _contains_shell_operator(argv: list[str]) -> bool:
    operator_tokens = {"&&", "||", "|", ";", ">", ">>", "<", "<<", "&"}
    operator_fragments = ("$(", "`")
    return any(token in operator_tokens or any(fragment in token for fragment in operator_fragments) for token in argv)


def _evaluate_node_command(argv: list[str], evidence: dict[str, Any]) -> SandboxDecision:
    blocked_flags = {"-e", "--eval", "-p", "--print", "-r", "--require", "--import", "--loader"}
    for token in argv[1:]:
        if (
            token in blocked_flags
            or token.startswith("--eval=")
            or token.startswith("--print=")
            or token.startswith("--require=")
            or token.startswith("--import=")
            or token.startswith("--loader=")
        ):
            return SandboxDecision(SandboxVerdict.DENY, "node eval/print/preload flags are not allowed", evidence)
    script = _first_node_script_arg(argv)
    if script is None:
        return SandboxDecision(SandboxVerdict.DENY, "node command must target a workspace script", evidence)
    workspace_check = _workspace_path_decision(script)
    if workspace_check is not None:
        return workspace_check
    return SandboxDecision(
        SandboxVerdict.ALLOW,
        "controlled node command has passed sandbox checks",
        evidence | {"script": script},
    )


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
        if token == "--":
            continue
        if token.startswith("-"):
            continue
        return token
    return None


def _workspace_path_decision(raw_path: str) -> SandboxDecision | None:
    root = Path(os.getenv("HIFY_WORKSPACE_ROOT") or Path.cwd()).resolve()
    candidate = (root / raw_path).resolve()
    if candidate != root and root in candidate.parents:
        return None
    return SandboxDecision(
        verdict=SandboxVerdict.DENY,
        reason="command script path must stay inside workspace",
        evidence={"toolName": "run_shell", "path": raw_path},
    )
