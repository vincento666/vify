from dataclasses import dataclass
from enum import StrEnum
import os
from pathlib import Path
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
            return SandboxDecision(
                verdict=SandboxVerdict.DENY,
                reason="shell-like execution is blocked by the Phase 1 sandbox",
                evidence={"toolName": tool_name, "command": str(tool_input.get("command") or "")},
            )
        if tool_name in {"read_workspace_file", "write_workspace_file"}:
            root = Path(os.getenv("HIFY_WORKSPACE_ROOT") or Path.cwd()).resolve()
            raw_path = str(tool_input.get("path") or "").strip()
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
