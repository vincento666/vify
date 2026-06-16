from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskCommandType(StrEnum):
    ADD_TASK = "ADD_TASK"
    RETAIN_TASK = "RETAIN_TASK"
    CANCEL_TASK = "CANCEL_TASK"
    SUSPEND_TASK = "SUSPEND_TASK"
    RESUME_TASK = "RESUME_TASK"
    CALL_WORKER = "CALL_WORKER"
    FINAL = "FINAL"


@dataclass(frozen=True)
class TaskItem:
    id: int | None
    session_id: int
    task_key: str
    task_type: str
    business_key: str
    short_id: str
    status: TaskStatus
    worker_type: str
    worker_ref: str
    checkpoint: dict[str, Any] = field(default_factory=dict)
    input_snapshot: dict[str, Any] = field(default_factory=dict)
    last_result: dict[str, Any] = field(default_factory=dict)
    proposed_actions: list[dict[str, Any]] = field(default_factory=list)
    version: int = 1


@dataclass(frozen=True)
class TaskCommand:
    type: TaskCommandType
    task_key: str = ""
    task_type: str = ""
    business_key: str = ""
    worker_type: str = ""
    worker_ref: str = ""
    reason: str = ""
    input_snapshot: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkerResult:
    task_id: int
    worker_type: str
    status: TaskStatus
    worker_run_id: str | None = None
    worker_async_refs: dict[str, Any] = field(default_factory=dict)
    operator_recommendation: str = ""
    customer_reply_draft: str = ""
    missing_fields: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    safe_auto_actions_done: list[dict[str, Any]] = field(default_factory=list)
    proposed_actions: list[dict[str, Any]] = field(default_factory=list)
    checkpoint: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    error: dict[str, Any] | None = None


@dataclass(frozen=True)
class ProposedAction:
    id: int | None
    session_id: int
    run_id: int
    task_id: int | None
    action_key: str
    action_type: str
    title: str
    payload: dict[str, Any]
    status: str = "PENDING"


@dataclass(frozen=True)
class RuntimeEvent:
    id: int | None
    session_id: int
    run_id: int | None
    sequence: int
    type: str
    visibility: str = "operator"
    source: str = "customer_assistant"
    task_id: int | None = None
    parent_span_id: str | None = None
    span_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None


@dataclass(frozen=True)
class AssistantTurnResult:
    run_id: int
    session_id: int
    reply_type: str
    operator_recommendation: str
    customer_reply_draft: str
    task_summaries: list[dict[str, Any]] = field(default_factory=list)
    proposed_actions: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class TaskLedger:
    session_id: int
    tasks: tuple[TaskItem, ...] = ()

    def by_key(self, task_key: str) -> TaskItem | None:
        for task in self.tasks:
            if task.task_key == task_key:
                return task
        return None

    def active_tasks(self) -> tuple[TaskItem, ...]:
        active_statuses = {TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.WAITING}
        return tuple(task for task in self.tasks if task.status in active_statuses)
