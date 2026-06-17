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
        manifest = ToolManifest(
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
        return cls({"echo_context": (manifest, _echo_context)})

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
