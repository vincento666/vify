from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ChildExecutionReference:
    agent_type: str
    child_run_id: str
    event_stream_ref: str
    result_ref: str
    worker_async_refs: dict[str, Any]
    cancellation: dict[str, Any]


class ChildExecutionReferenceAdapter(Protocol):
    @property
    def tool_name(self) -> str: ...

    @property
    def description(self) -> str: ...

    @property
    def read_resources(self) -> list[str]: ...

    def resolve(self, *, session_id: int, run_id: int) -> ChildExecutionReference: ...


__all__ = [
    "ChildExecutionReference",
    "ChildExecutionReferenceAdapter",
]
