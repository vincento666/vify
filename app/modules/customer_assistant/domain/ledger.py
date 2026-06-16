from dataclasses import dataclass
from typing import Any

from app.modules.customer_assistant.domain.models import TaskCommand, TaskCommandType, TaskItem, TaskStatus, WorkerResult
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository


@dataclass(frozen=True)
class LedgerMutationResult:
    tasks: tuple[TaskItem, ...]
    ready_tasks: tuple[TaskItem, ...]
    events: tuple[dict[str, Any], ...]


class CustomerAssistantLedger:
    def __init__(self, repository: CustomerAssistantRepository) -> None:
        self._repository = repository

    def apply_commands(
        self,
        session_id: int,
        run_id: int,
        message: str,
        commands: list[TaskCommand],
        actor: str = "customer",
    ) -> LedgerMutationResult:
        ready: list[TaskItem] = []
        events: list[dict[str, Any]] = []
        for command in commands:
            if command.type == TaskCommandType.ADD_TASK:
                existing = self._repository.get_task_by_key(session_id, command.task_key)
                task_row = self._repository.upsert_task(
                    session_id=session_id,
                    task_key=command.task_key,
                    task_type=command.task_type,
                    business_key=command.business_key,
                    worker_type=command.worker_type,
                    worker_ref=command.worker_ref,
                    input_snapshot={**command.input_snapshot, "message": message, "actor": actor},
                )
                event_type = "task_retained" if existing else "task_added"
                events.append(
                    self._repository.append_event(
                        session_id=session_id,
                        run_id=run_id,
                        event_type=event_type,
                        task_id=int(task_row["id"]),
                        payload={"taskKey": command.task_key},
                        actor=actor,
                    )
                )
                ready.append(_task_item(task_row))
            elif command.type == TaskCommandType.RETAIN_TASK:
                retained_row = self._repository.get_task_by_key(session_id, command.task_key)
                if retained_row is None:
                    continue
                events.append(
                    self._repository.append_event(
                        session_id=session_id,
                        run_id=run_id,
                        event_type="task_retained",
                        task_id=int(retained_row["id"]),
                        payload={"taskKey": command.task_key},
                        actor=actor,
                    )
                )
                task = _task_item(retained_row)
                if task.status in {TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.WAITING}:
                    ready.append(task)
            elif command.type == TaskCommandType.CANCEL_TASK:
                cancelled_row = self._repository.get_task_by_key(session_id, command.task_key)
                if cancelled_row is None:
                    continue
                cancelled = self._repository.update_task(int(cancelled_row["id"]), status=TaskStatus.CANCELLED.value)
                events.append(
                    self._repository.append_event(
                        session_id=session_id,
                        run_id=run_id,
                        event_type="task_cancelled",
                        task_id=int(cancelled["id"]),
                        payload={"taskKey": command.task_key},
                        actor=actor,
                    )
                )
            elif command.type in {TaskCommandType.SUSPEND_TASK, TaskCommandType.RESUME_TASK}:
                resumed_row = self._repository.get_task_by_key(session_id, command.task_key)
                if resumed_row is None:
                    continue
                status = TaskStatus.WAITING if command.type == TaskCommandType.SUSPEND_TASK else TaskStatus.RUNNING
                updated = self._repository.update_task(int(resumed_row["id"]), status=status.value)
                event_type = "task_waiting" if status == TaskStatus.WAITING else "task_retained"
                events.append(
                    self._repository.append_event(
                        session_id=session_id,
                        run_id=run_id,
                        event_type=event_type,
                        task_id=int(updated["id"]),
                        payload={"taskKey": command.task_key},
                        actor=actor,
                    )
                )
                ready.append(_task_item(updated))
        tasks = tuple(_task_item(row) for row in self._repository.list_tasks(session_id))
        return LedgerMutationResult(tasks=tasks, ready_tasks=tuple(ready), events=tuple(events))

    def apply_worker_results(
        self,
        session_id: int,
        run_id: int,
        results: list[WorkerResult],
        actor: str = "customer",
    ) -> tuple[TaskItem, ...]:
        updated_tasks: list[TaskItem] = []
        for result in results:
            task = self._repository.get_task(result.task_id)
            if task is None:
                continue
            proposed_actions = list(task.get("proposed_actions_json") or [])
            proposed_actions.extend(
                _persisted_action_payloads(
                    self._repository,
                    session_id=session_id,
                    run_id=run_id,
                    task_id=result.task_id,
                    result=result,
                )
            )
            updated = self._repository.update_task(
                result.task_id,
                status=result.status.value,
                checkpoint=result.checkpoint,
                last_result=_worker_result_payload(result),
                proposed_actions=proposed_actions,
            )
            self._repository.append_event(
                session_id=session_id,
                run_id=run_id,
                event_type=_event_type_for_result(result),
                task_id=result.task_id,
                payload={"taskKey": updated["task_key"], "workerType": result.worker_type},
                actor=actor,
            )
            updated_tasks.append(_task_item(updated))
        return tuple(updated_tasks)


def _task_item(row: dict[str, Any]) -> TaskItem:
    return TaskItem(
        id=int(row["id"]),
        session_id=int(row["session_id"]),
        task_key=str(row["task_key"]),
        task_type=str(row["task_type"]),
        business_key=str(row["business_key"]),
        short_id=str(row["short_id"]),
        status=TaskStatus(str(row["status"])),
        worker_type=str(row["worker_type"]),
        worker_ref=str(row["worker_ref"]),
        checkpoint=dict(row.get("checkpoint_json") or {}),
        input_snapshot=dict(row.get("input_snapshot_json") or {}),
        last_result=dict(row.get("last_result_json") or {}),
        proposed_actions=list(row.get("proposed_actions_json") or []),
        version=int(row.get("version") or 1),
    )


def _worker_result_payload(result: WorkerResult) -> dict[str, Any]:
    return {
        "taskId": result.task_id,
        "workerType": result.worker_type,
        "workerRunId": result.worker_run_id,
        "workerAsyncRefs": dict(result.worker_async_refs),
        "status": result.status.value,
        "operatorRecommendation": result.operator_recommendation,
        "customerReplyDraft": result.customer_reply_draft,
        "missingFields": list(result.missing_fields),
        "evidence": dict(result.evidence),
        "safeAutoActionsDone": [dict(action) for action in result.safe_auto_actions_done],
        "proposedActions": _proposed_action_payloads(result),
        "checkpoint": dict(result.checkpoint),
        "events": [dict(event) for event in result.events],
        "error": dict(result.error) if result.error else None,
    }


def _proposed_action_payloads(result: WorkerResult) -> list[dict[str, Any]]:
    return [dict(action) for action in result.proposed_actions]


def _persisted_action_payloads(
    repository: CustomerAssistantRepository,
    *,
    session_id: int,
    run_id: int,
    task_id: int,
    result: WorkerResult,
) -> list[dict[str, Any]]:
    persisted: list[dict[str, Any]] = []
    for action in result.proposed_actions:
        action_key = str(action.get("actionKey") or action.get("action_key") or "")
        action_type = str(action.get("actionType") or action.get("action_type") or "")
        if not action_key or not action_type:
            continue
        row = repository.upsert_proposed_action(
            session_id=session_id,
            run_id=run_id,
            task_id=task_id,
            action_key=action_key,
            action_type=action_type,
            title=str(action.get("title") or action_type),
            payload=dict(action.get("payload") or {}),
        )
        persisted.append(
            {
                "id": row["id"],
                "actionKey": row["action_key"],
                "actionType": row["action_type"],
                "title": row["title"],
                "payload": row["payload"] or {},
                "status": row["status"],
            }
        )
    return persisted


def _event_type_for_result(result: WorkerResult) -> str:
    if result.status == TaskStatus.COMPLETED:
        return "task_completed"
    if result.status == TaskStatus.WAITING:
        return "task_waiting"
    if result.status == TaskStatus.FAILED:
        return "task_failed"
    return "worker_result_received"
