from __future__ import annotations

import json
import time
import unittest
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session, sessionmaker

from app.modules.customer_assistant.domain.models import TaskItem, TaskStatus, WorkerResult
from app.modules.customer_assistant.domain.scheduler import LocalWorkerScheduler
from app.modules.customer_assistant.domain.service import CustomerAssistantService
from app.modules.customer_assistant.domain.worker_profiles import CustomerAssistantWorkerProfileCatalog
from app.modules.customer_assistant.domain.worker_runtime import CustomerAssistantWorkerRuntime
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository
from app.modules.customer_assistant.infra.schema import (
    customer_assistant_tables,
    register_customer_assistant_tables,
)
from tests.support.mysql import mysql8_session


class CustomerAssistantWorkerStateMachineTest(unittest.TestCase):
    def test_async_worker_runtime_consumes_full_task_state_machine(self) -> None:
        cases = [
            _StateCase(
                name="running",
                worker=_StateWorker(TaskStatus.COMPLETED, sleep_seconds=0.4),
                wait_deadline_seconds=0.01,
                expected_task_status="RUNNING",
                expected_worker_status="RUNNING",
                expected_event_type="worker_result_received",
            ),
            _StateCase(
                name="waiting",
                worker=_StateWorker(TaskStatus.WAITING),
                wait_deadline_seconds=0.2,
                expected_task_status="WAITING",
                expected_worker_status="COMPLETED",
                expected_event_type="task_waiting",
            ),
            _StateCase(
                name="completed",
                worker=_StateWorker(TaskStatus.COMPLETED),
                wait_deadline_seconds=0.2,
                expected_task_status="COMPLETED",
                expected_worker_status="COMPLETED",
                expected_event_type="task_completed",
            ),
            _StateCase(
                name="failed",
                worker=_StateWorker(TaskStatus.FAILED),
                wait_deadline_seconds=0.2,
                expected_task_status="FAILED",
                expected_worker_status="FAILED",
                expected_event_type="task_failed",
            ),
            _StateCase(
                name="cancelled",
                worker=_StateWorker(TaskStatus.CANCELLED),
                wait_deadline_seconds=0.2,
                expected_task_status="CANCELLED",
                expected_worker_status="CANCELLED",
                expected_event_type="task_cancelled",
            ),
        ]
        for case in cases:
            with self.subTest(case=case.name), _session() as session:
                service = _service_for_case(session, case)
                assistant_session = service.create_session()

                turn = service.handle_turn(
                    int(assistant_session["id"]),
                    "行李额度是多少",
                    f"2165-worker-state-{case.name}-{time.time_ns()}",
                )
                summary = turn["taskSummaries"][0]
                refs = summary["workerAsyncRefs"]
                worker_run = service.get_worker_run(refs["workerRunId"])
                events = service.list_events(int(assistant_session["id"]))["list"]

                self.assertEqual(summary["status"], case.expected_task_status)
                self.assertEqual(summary["lastResult"]["status"], case.expected_task_status)
                self.assertEqual(worker_run["status"], case.expected_worker_status)
                self.assertIn(case.expected_event_type, [event["type"] for event in events])

                if case.name == "running":
                    time.sleep(0.45)


class _StateCase:
    def __init__(
        self,
        *,
        name: str,
        worker: "_StateWorker",
        wait_deadline_seconds: float,
        expected_task_status: str,
        expected_worker_status: str,
        expected_event_type: str,
    ) -> None:
        self.name = name
        self.worker = worker
        self.wait_deadline_seconds = wait_deadline_seconds
        self.expected_task_status = expected_task_status
        self.expected_worker_status = expected_worker_status
        self.expected_event_type = expected_event_type


class _StateWorker:
    def __init__(self, status: TaskStatus, *, sleep_seconds: float = 0.0) -> None:
        self._status = status
        self._sleep_seconds = sleep_seconds

    def run(self, task: TaskItem, message: str) -> WorkerResult:
        if self._sleep_seconds:
            time.sleep(self._sleep_seconds)
        return WorkerResult(
            task_id=int(task.id or 0),
            worker_type=task.worker_type,
            status=self._status,
            operator_recommendation=f"{self._status.value.lower()} recommendation for {message}",
            customer_reply_draft="请提供客票舱位和航司。" if self._status == TaskStatus.WAITING else "",
            missing_fields=["客票舱位和航司"] if self._status == TaskStatus.WAITING else [],
            evidence={"stateMachineCase": self._status.value},
            events=[
                {
                    "type": f"state_machine_{self._status.value.lower()}",
                    "source": "state_machine_test",
                    "payload": {"status": self._status.value},
                }
            ],
            error={"code": "STATE_MACHINE_FAILED", "message": "worker failed"}
            if self._status == TaskStatus.FAILED
            else None,
        )


def _service_for_case(session: Session, case: _StateCase) -> CustomerAssistantService:
    factory = sessionmaker(bind=session.get_bind(), autoflush=False, autocommit=False, expire_on_commit=False)
    workers = {"stub_qa": case.worker}
    return CustomerAssistantService(
        CustomerAssistantRepository(session),
        scheduler=LocalWorkerScheduler(workers),
        async_worker_runtime=CustomerAssistantWorkerRuntime(
            workers=workers,
            session_factory=factory,
            wait_deadline_seconds=case.wait_deadline_seconds,
            task_timeout_seconds=1.0,
        ),
        worker_profiles=_legacy_stub_baggage_profiles(),
    )


def _legacy_stub_baggage_profiles() -> CustomerAssistantWorkerProfileCatalog:
    return CustomerAssistantWorkerProfileCatalog.from_json(
        json.dumps(
            {
                "profiles": [
                    {
                        "profileId": "state_machine_baggage_stub",
                        "taskKey": "baggage_qa",
                        "taskType": "QA",
                        "workerType": "stub_qa",
                        "workerRef": "state_machine",
                        "modelPolicyRef": "state_machine_model",
                        "promptRef": "state_machine_prompt",
                        "riskPolicyRef": "read_only",
                    }
                ]
            }
        )
    )


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session(
        "customer_assistant_worker_state_machine",
        tables=customer_assistant_tables(),
        register=register_customer_assistant_tables,
    ) as session:
        yield session
