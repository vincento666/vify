from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError
from time import monotonic
from typing import Any

from sqlalchemy.orm import Session

from app.modules.customer_assistant.domain.models import TaskItem, TaskStatus, WorkerResult
from app.modules.customer_assistant.domain.worker import TaskWorker
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository


WORKER_RUN_PREFIX = "customer-assistant-worker-run-"
DEFAULT_WAIT_DEADLINE_SECONDS = 0.1


@dataclass(frozen=True)
class _StartedWorkerRun:
    task: TaskItem
    worker_run_id: int
    wait_deadline_seconds: float
    future: Future[WorkerResult] | None = None
    immediate_result: WorkerResult | None = None


class CustomerAssistantWorkerRuntime:
    def __init__(
        self,
        *,
        workers: dict[str, TaskWorker],
        session_factory: Callable[[], Session],
        async_worker_types: set[str] | None = None,
        wait_deadline_seconds: float | None = None,
        task_timeout_seconds: float = 5.0,
        max_concurrency: int = 4,
    ) -> None:
        self._workers = workers
        self._session_factory = session_factory
        self._async_worker_types = async_worker_types or {"stub_qa"}
        self._wait_deadline_seconds = wait_deadline_seconds
        self._task_timeout_seconds = task_timeout_seconds
        self._executor = ThreadPoolExecutor(max_workers=max(1, max_concurrency))

    def supports(self, task: TaskItem) -> bool:
        return task.worker_type in self._async_worker_types

    def start_and_wait(
        self,
        repository: CustomerAssistantRepository,
        *,
        session_id: int,
        parent_run_id: int,
        task: TaskItem,
        message: str,
        actor: str,
    ) -> WorkerResult:
        return self.start_many_and_wait(
            repository,
            session_id=session_id,
            parent_run_id=parent_run_id,
            tasks=[task],
            message=message,
            actor=actor,
        )[0]

    def start_many_and_wait(
        self,
        repository: CustomerAssistantRepository,
        *,
        session_id: int,
        parent_run_id: int,
        tasks: list[TaskItem],
        message: str,
        actor: str,
    ) -> list[WorkerResult]:
        started = [
            self._start_worker_run(
                repository,
                session_id=session_id,
                parent_run_id=parent_run_id,
                task=task,
                message=message,
                actor=actor,
            )
            for task in tasks
        ]
        return self._join_started_worker_runs(repository, started)

    def _start_worker_run(
        self,
        repository: CustomerAssistantRepository,
        *,
        session_id: int,
        parent_run_id: int,
        task: TaskItem,
        message: str,
        actor: str,
    ) -> _StartedWorkerRun:
        worker_run, replayed = repository.create_worker_run(
            session_id=session_id,
            parent_run_id=parent_run_id,
            task_id=int(task.id or 0),
            worker_type=task.worker_type,
            worker_ref=task.worker_ref,
            idempotency_key=_worker_idempotency_key(parent_run_id, task, message),
            request_hash=_worker_request_hash(task, message),
            input_payload={
                "message": message,
                "actor": actor,
                "task": {
                    "taskId": task.id,
                    "taskKey": task.task_key,
                    "taskType": task.task_type,
                    "taskVersion": task.version,
                    "workerType": task.worker_type,
                    "workerRef": task.worker_ref,
                },
            },
        )
        worker_run_id = int(worker_run["id"])
        wait_deadline_seconds = self._wait_deadline_for(task)
        if replayed and str(worker_run["status"]) in _TERMINAL_WORKER_STATUSES:
            return _StartedWorkerRun(
                task=task,
                worker_run_id=worker_run_id,
                wait_deadline_seconds=wait_deadline_seconds,
                immediate_result=worker_result_from_worker_run(task, worker_run, refs=worker_async_refs(worker_run_id)),
            )
        if replayed and str(worker_run["status"]) == "RUNNING":
            return _StartedWorkerRun(
                task=task,
                worker_run_id=worker_run_id,
                wait_deadline_seconds=wait_deadline_seconds,
                immediate_result=self._pending_result(
                    repository,
                    task,
                    worker_run_id,
                    wait_deadline_seconds=wait_deadline_seconds,
                ),
            )
        repository.mark_worker_running(worker_run_id)
        future = self._executor.submit(self._execute_worker_run, worker_run_id, task, message)
        return _StartedWorkerRun(
            task=task,
            worker_run_id=worker_run_id,
            wait_deadline_seconds=wait_deadline_seconds,
            future=future,
        )

    def _join_started_worker_runs(
        self,
        repository: CustomerAssistantRepository,
        started: list[_StartedWorkerRun],
    ) -> list[WorkerResult]:
        results: list[WorkerResult] = []
        join_started = monotonic()
        for worker_run in started:
            if worker_run.immediate_result is not None:
                results.append(worker_run.immediate_result)
                continue
            future = worker_run.future
            if future is None:
                results.append(
                    self._pending_result(
                        repository,
                        worker_run.task,
                        worker_run.worker_run_id,
                        wait_deadline_seconds=worker_run.wait_deadline_seconds,
                    )
                )
                continue
            remaining = worker_run.wait_deadline_seconds - (monotonic() - join_started)
            if remaining <= 0 and not future.done():
                results.append(
                    self._pending_result(
                        repository,
                        worker_run.task,
                        worker_run.worker_run_id,
                        wait_deadline_seconds=worker_run.wait_deadline_seconds,
                    )
                )
                continue
            try:
                results.append(future.result(timeout=max(0.0, remaining)))
            except TimeoutError:
                results.append(
                    self._pending_result(
                        repository,
                        worker_run.task,
                        worker_run.worker_run_id,
                        wait_deadline_seconds=worker_run.wait_deadline_seconds,
                    )
                )
        return results

    def _pending_result(
        self,
        repository: CustomerAssistantRepository,
        task: TaskItem,
        worker_run_id: int,
        *,
        wait_deadline_seconds: float,
    ) -> WorkerResult:
        refs = worker_async_refs(worker_run_id)
        repository.append_worker_event(
            worker_run_id,
            "worker_run_pending",
            {"workerRunId": refs["workerRunId"], "status": "RUNNING", "waitDeadlineSeconds": wait_deadline_seconds},
        )
        return WorkerResult(
            task_id=int(task.id or 0),
            worker_type=task.worker_type,
            status=TaskStatus.RUNNING,
            worker_run_id=str(refs["workerRunId"]),
            worker_async_refs=refs,
            operator_recommendation=f"required worker evidence is pending for {task.task_key}",
            customer_reply_draft="我正在继续处理，请稍等。",
            events=[
                {
                    "type": "worker_run_pending",
                    "source": "customer_assistant_worker",
                    "payload": {"workerRunId": refs["workerRunId"], "status": "RUNNING"},
                }
            ],
        )

    def _wait_deadline_for(self, task: TaskItem) -> float:
        if self._wait_deadline_seconds is not None:
            return self._wait_deadline_seconds
        if task.worker_type == "chatflow_sop":
            return self._task_timeout_seconds
        return DEFAULT_WAIT_DEADLINE_SECONDS

    def _execute_worker_run(self, worker_run_id: int, task: TaskItem, message: str) -> WorkerResult:
        with self._session_factory() as session:
            repository = CustomerAssistantRepository(session)
            repository.mark_worker_running(worker_run_id)
            worker = self._workers.get(task.worker_type)
            if worker is None:
                result = WorkerResult(
                    task_id=int(task.id or 0),
                    worker_type=task.worker_type,
                    status=TaskStatus.FAILED,
                    error={"code": "WORKER_NOT_FOUND", "message": f"No worker registered for type: {task.worker_type}"},
                )
            else:
                result = self._run_with_timeout(worker, task, message)
            refs = worker_async_refs(worker_run_id)
            result = _with_refs(result, refs)
            for event in result.events:
                repository.append_worker_event(
                    worker_run_id,
                    str(event.get("type") or "worker_result_received"),
                    dict(event.get("payload") or {}),
                    source=str(event.get("source") or result.worker_type),
                )
            terminal_status = _worker_terminal_status(result)
            repository.complete_worker_run(
                worker_run_id,
                status=terminal_status,
                result_payload=_worker_result_payload(result),
                error=result.error,
            )
            return result

    def _run_with_timeout(self, worker: TaskWorker, task: TaskItem, message: str) -> WorkerResult:
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(worker.run, task, message)
            return future.result(timeout=self._task_timeout_seconds)
        except TimeoutError:
            events = [
                {
                    "type": "worker_timeout_started",
                    "source": "customer_assistant_worker",
                    "payload": {"taskId": task.id, "workerType": task.worker_type},
                },
                {
                    "type": "worker_timed_out",
                    "source": "customer_assistant_worker",
                    "payload": {"taskId": task.id, "workerType": task.worker_type},
                },
            ]
            evidence: dict[str, Any] = {}
            if task.worker_type == "chatflow_sop":
                cancellation = {
                    "supported": False,
                    "reason": "Chatflow v2 cooperative cancellation is not supported by this worker runtime.",
                }
                evidence["chatflowCancellation"] = cancellation
                events.append(
                    {
                        "type": "chatflow_v2_cancel_unsupported",
                        "source": "customer_assistant_worker",
                        "payload": {
                            "taskId": task.id,
                            "workerType": task.worker_type,
                            "cancellation": cancellation,
                        },
                    }
                )
            return WorkerResult(
                task_id=int(task.id or 0),
                worker_type=task.worker_type,
                status=TaskStatus.FAILED,
                evidence=evidence,
                events=events,
                error={"code": "WORKER_TIMEOUT", "message": "worker timed out"},
            )
        except Exception as exc:
            return WorkerResult(
                task_id=int(task.id or 0),
                worker_type=task.worker_type,
                status=TaskStatus.FAILED,
                error={"code": "WORKER_FAILED", "message": str(exc)},
            )
        finally:
            executor.shutdown(wait=False, cancel_futures=True)


def worker_async_refs(worker_run_id: int) -> dict[str, Any]:
    public_id = worker_run_public_id(worker_run_id)
    base = f"/api/v1/customer-assistant/worker-runs/{public_id}"
    return {
        "supported": True,
        "workerRunId": public_id,
        "workerStatusRef": base,
        "workerEventsRef": f"{base}/events",
        "workerEventStreamRef": f"{base}/events/stream?afterSequence=0",
        "workerResultRef": f"{base}/result",
        "scope": "customer_assistant_worker_run",
    }


def worker_run_public_id(worker_run_id: int) -> str:
    return f"{WORKER_RUN_PREFIX}{worker_run_id}"


def parse_worker_run_public_id(public_id: str) -> int:
    if not public_id.startswith(WORKER_RUN_PREFIX):
        raise ValueError("Invalid customer assistant worker run id")
    return int(public_id.removeprefix(WORKER_RUN_PREFIX))


def _with_refs(result: WorkerResult, refs: dict[str, Any]) -> WorkerResult:
    return WorkerResult(
        task_id=result.task_id,
        worker_type=result.worker_type,
        status=result.status,
        worker_run_id=str(refs["workerRunId"]),
        worker_async_refs=refs,
        operator_recommendation=result.operator_recommendation,
        customer_reply_draft=result.customer_reply_draft,
        missing_fields=list(result.missing_fields),
        evidence=dict(result.evidence),
        safe_auto_actions_done=[dict(action) for action in result.safe_auto_actions_done],
        proposed_actions=[dict(action) for action in result.proposed_actions],
        checkpoint=dict(result.checkpoint),
        events=[dict(event) for event in result.events],
        error=dict(result.error) if result.error else None,
    )


def worker_result_from_worker_run(task: TaskItem, worker_run: dict[str, Any], refs: dict[str, Any]) -> WorkerResult:
    payload = dict(worker_run.get("result_payload") or {})
    status = TaskStatus(str(payload.get("status") or "FAILED"))
    return WorkerResult(
        task_id=int(task.id or worker_run["task_id"]),
        worker_type=str(worker_run["worker_type"]),
        status=status,
        worker_run_id=str(refs["workerRunId"]),
        worker_async_refs=refs,
        operator_recommendation=str(payload.get("operatorRecommendation") or ""),
        customer_reply_draft=str(payload.get("customerReplyDraft") or ""),
        missing_fields=list(payload.get("missingFields") or []),
        evidence=dict(payload.get("evidence") or {}),
        safe_auto_actions_done=[dict(action) for action in payload.get("safeAutoActionsDone") or []],
        proposed_actions=[dict(action) for action in payload.get("proposedActions") or []],
        checkpoint=dict(payload.get("checkpoint") or {}),
        events=[dict(event) for event in payload.get("events") or []],
        error=dict(payload.get("error") or {}) or None,
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
        "proposedActions": [dict(action) for action in result.proposed_actions],
        "checkpoint": dict(result.checkpoint),
        "events": [dict(event) for event in result.events],
        "error": dict(result.error) if result.error else None,
    }


def _worker_terminal_status(result: WorkerResult) -> str:
    if result.error and result.error.get("code") == "WORKER_TIMEOUT":
        return "TIMED_OUT"
    if result.status == TaskStatus.FAILED:
        return "FAILED"
    if result.status == TaskStatus.CANCELLED:
        return "CANCELLED"
    return "COMPLETED"


def _worker_idempotency_key(parent_run_id: int, task: TaskItem, message: str) -> str:
    return (
        f"run:{parent_run_id}:task:{task.id}:version:{task.version}:"
        f"worker:{task.worker_type}:{task.worker_ref}:request:{_message_hash(message)}"
    )


def _worker_request_hash(task: TaskItem, message: str) -> str:
    raw = json.dumps(
        {
            "taskId": task.id,
            "taskKey": task.task_key,
            "taskVersion": task.version,
            "workerType": task.worker_type,
            "workerRef": task.worker_ref,
            "message": message,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _message_hash(message: str) -> str:
    return hashlib.sha256(message.encode("utf-8")).hexdigest()[:16]


_TERMINAL_WORKER_STATUSES = {"COMPLETED", "FAILED", "TIMED_OUT", "CANCELLED", "CANCEL_UNSUPPORTED"}
