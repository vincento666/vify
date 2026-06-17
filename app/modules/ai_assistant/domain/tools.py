from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable


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
            description="Echo the current user message and safe context for harness verification.",
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
            description="Request a high-risk customer profile mutation as a proposed action.",
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
            description="Shell-like execution placeholder blocked by sandbox policy.",
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
        return cls(
            {
                "echo_context": (echo_manifest, _echo_context),
                "update_customer_profile": (business_write_manifest, _blocked_write),
                "run_shell": (shell_manifest, _blocked_write),
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
