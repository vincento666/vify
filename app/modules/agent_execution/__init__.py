from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from app.modules.agent_execution.correlation import (
    build_activity_correlation_ids,
    tool_activity_correlation_ids,
)


class AgentExecutionStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_active(self) -> bool:
        return self in {
            AgentExecutionStatus.QUEUED,
            AgentExecutionStatus.RUNNING,
            AgentExecutionStatus.WAITING_APPROVAL,
        }

    @classmethod
    def from_value(cls, value: object) -> AgentExecutionStatus:
        normalized = str(value or "").strip().lower()
        aliases = {
            "pending": cls.QUEUED,
            "waiting": cls.WAITING_APPROVAL,
            "waiting_approval": cls.WAITING_APPROVAL,
            "approved": cls.COMPLETED,
            "timed_out": cls.FAILED,
        }
        if normalized in aliases:
            return aliases[normalized]
        try:
            return cls(normalized)
        except ValueError:
            return cls.FAILED


@dataclass(frozen=True)
class AgentExecutionCapabilities:
    spawn: bool
    attach: bool
    observe: bool
    cancel: bool


class AgentExecutionCapabilityError(RuntimeError):
    def __init__(self, capability: str) -> None:
        self.capability = capability
        super().__init__(f"Agent execution provider does not support {capability}")


class AgentExecutionTransitionError(RuntimeError):
    pass


def transition_agent_execution_status(
    current: AgentExecutionStatus,
    next_status: AgentExecutionStatus,
    *,
    reopen: bool = False,
) -> AgentExecutionStatus:
    if current == next_status:
        return current
    terminal = {
        AgentExecutionStatus.COMPLETED,
        AgentExecutionStatus.FAILED,
        AgentExecutionStatus.CANCELLED,
    }
    if current in terminal:
        if reopen and next_status in {
            AgentExecutionStatus.QUEUED,
            AgentExecutionStatus.RUNNING,
            AgentExecutionStatus.WAITING_APPROVAL,
        }:
            return next_status
        raise AgentExecutionTransitionError(
            f"Terminal agent execution cannot transition from {current} to {next_status}"
        )
    allowed = {
        AgentExecutionStatus.QUEUED: {
            AgentExecutionStatus.RUNNING,
            AgentExecutionStatus.WAITING_APPROVAL,
            *terminal,
        },
        AgentExecutionStatus.RUNNING: {
            AgentExecutionStatus.WAITING_APPROVAL,
            *terminal,
        },
        AgentExecutionStatus.WAITING_APPROVAL: {
            AgentExecutionStatus.RUNNING,
            *terminal,
        },
    }
    if next_status not in allowed[current]:
        raise AgentExecutionTransitionError(
            f"Invalid agent execution transition from {current} to {next_status}"
        )
    return next_status


@dataclass(frozen=True)
class SubagentExecutionRef:
    execution_id: str
    provider: str
    child_run_id: str
    agent_type: str
    display_name: str
    status: AgentExecutionStatus
    status_ref: str
    event_stream_ref: str
    result_ref: str
    capabilities: AgentExecutionCapabilities
    parent_execution_id: str | None = None
    current_summary: str = ""
    started_at: str | None = None
    completed_at: str | None = None
    scope: dict[str, Any] = field(default_factory=dict)
    audit: dict[str, Any] = field(default_factory=dict)
    runtime_refs: dict[str, Any] = field(default_factory=dict)
    cancellation: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class SubagentExecutionProvider(Protocol):
    @property
    def provider(self) -> str: ...

    @property
    def display_name(self) -> str: ...

    @property
    def capabilities(self) -> AgentExecutionCapabilities: ...

    def spawn(
        self,
        *,
        parent_execution_id: str,
        input_payload: dict[str, Any],
    ) -> SubagentExecutionRef: ...

    def attach(
        self,
        *,
        parent_execution_id: str,
        session_id: int,
        run_id: int,
    ) -> SubagentExecutionRef: ...

    def observe(self, *, execution_id: str) -> SubagentExecutionRef: ...

    def cancel(
        self,
        *,
        execution_id: str,
        actor_id: str,
    ) -> SubagentExecutionRef: ...


__all__ = [
    "AgentExecutionCapabilities",
    "AgentExecutionCapabilityError",
    "AgentExecutionStatus",
    "AgentExecutionTransitionError",
    "SubagentExecutionProvider",
    "SubagentExecutionRef",
    "build_activity_correlation_ids",
    "transition_agent_execution_status",
    "tool_activity_correlation_ids",
]
