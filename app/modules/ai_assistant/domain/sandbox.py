from dataclasses import dataclass
from enum import StrEnum
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
        return SandboxDecision(
            verdict=SandboxVerdict.ALLOW,
            reason="tool is allowed by the Phase 1 sandbox",
            evidence={"toolName": tool_name},
        )
