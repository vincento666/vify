from contextlib import contextmanager
import json
import unittest
from collections.abc import Iterator
import threading
import time

from sqlalchemy.orm import Session, sessionmaker

from tests.support.mysql import mysql8_session
from app.modules.customer_assistant.domain.ledger import CustomerAssistantLedger
from app.modules.customer_assistant.domain.models import TaskItem, TaskStatus, WorkerResult
from app.modules.customer_assistant.domain.scheduler import LocalWorkerScheduler
from app.modules.customer_assistant.domain.service import CustomerAssistantService
from app.modules.customer_assistant.domain.worker_runtime import CustomerAssistantWorkerRuntime
from app.modules.customer_assistant.domain.worker_profiles import CustomerAssistantWorkerProfileCatalog
from app.modules.customer_assistant.domain.workers import ChatflowSopWorker, RecommendationAggregator, StubQaWorker
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository
from app.modules.customer_assistant.infra.schema import (
    customer_assistant_tables,
    register_customer_assistant_tables,
)
from app.modules.runtime_lab.domain.sop_adapter import FakeSopRuntimeAdapter


class CustomerAssistantWorkersTest(unittest.TestCase):
    def test_chatflow_sop_worker_waits_continues_and_proposes_refund_submit(self) -> None:
        worker = ChatflowSopWorker(FakeSopRuntimeAdapter())
        task = _task(1, "refund_ticket", "chatflow_sop", "refund_ticket")

        started = worker.run(task, "我要退票")
        continued = worker.run(
            _task(1, "refund_ticket", "chatflow_sop", "refund_ticket", checkpoint=started.checkpoint),
            "订单号 TK-100",
        )
        completed = worker.run(
            _task(1, "refund_ticket", "chatflow_sop", "refund_ticket", checkpoint=continued.checkpoint),
            "确认",
        )

        self.assertEqual(started.status, TaskStatus.WAITING)
        self.assertIn("订单号", started.customer_reply_draft)
        self.assertEqual(continued.status, TaskStatus.WAITING)
        self.assertEqual(continued.checkpoint["currentStep"], "confirm")
        self.assertEqual(completed.status, TaskStatus.COMPLETED)
        self.assertEqual(completed.proposed_actions[0]["actionType"], "submit_refund")
        self.assertEqual(completed.proposed_actions[0]["payload"]["orderNo"], "TK-100")

    def test_default_baggage_profile_runs_deterministic_chatflow_worker_without_stub_evidence(self) -> None:
        profile = CustomerAssistantWorkerProfileCatalog.default().resolve("baggage_qa")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.worker_type, "chatflow_sop")
        self.assertEqual(profile.worker_ref, "baggage_service")

        result = ChatflowSopWorker(FakeSopRuntimeAdapter()).run(
            _task(2, profile.task_key, profile.worker_type, profile.worker_ref),
            "行李额多少？",
        )

        serialized = json.dumps(
            {
                "workerType": result.worker_type,
                "evidence": result.evidence,
                "events": result.events,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        self.assertEqual(result.worker_type, "chatflow_sop")
        self.assertEqual(result.status, TaskStatus.WAITING)
        self.assertIn("行李", result.customer_reply_draft)
        self.assertEqual(result.evidence["sopId"], "baggage_service")
        self.assertNotIn("stub_qa", serialized)

    def test_stub_qa_and_aggregator_return_separate_operator_and_customer_text(self) -> None:
        qa_result = StubQaWorker().run(_task(2, "baggage_qa", "stub_qa", "baggage_allowance"), "行李额多少？")

        result = RecommendationAggregator().aggregate(
            run_id=9,
            session_id=3,
            task_summaries=[{"taskKey": "baggage_qa", "status": "COMPLETED"}],
            worker_results=[qa_result],
            proposed_actions=[],
            events=[],
        )

        self.assertEqual(qa_result.status, TaskStatus.COMPLETED)
        self.assertIn("手提行李", qa_result.customer_reply_draft)
        self.assertIn("Operator", result.operator_recommendation)
        self.assertNotEqual(result.operator_recommendation, result.customer_reply_draft)
        self.assertEqual(result.task_summaries[0]["taskKey"], "baggage_qa")

    def test_high_risk_worker_action_is_persisted_as_pending_proposed_action(self) -> None:
        with _session() as session:
            repository = CustomerAssistantRepository(session)
            assistant_session = repository.create_session()
            run, _ = repository.create_run(
                int(assistant_session["id"]),
                idempotency_key="workers-1",
                request_hash="hash",
                input_payload={"message": "确认"},
            )
            task = repository.upsert_task(
                session_id=int(assistant_session["id"]),
                task_key="refund_ticket",
                task_type="REFUND",
                business_key="refund_ticket",
                worker_type="chatflow_sop",
                worker_ref="refund_ticket",
            )
            worker = ChatflowSopWorker(FakeSopRuntimeAdapter())
            started = worker.run(_task(int(task["id"]), "refund_ticket", "chatflow_sop", "refund_ticket"), "我要退票")
            continued = worker.run(
                _task(int(task["id"]), "refund_ticket", "chatflow_sop", "refund_ticket", started.checkpoint),
                "订单号 TK-100",
            )
            completed = worker.run(
                _task(int(task["id"]), "refund_ticket", "chatflow_sop", "refund_ticket", continued.checkpoint),
                "确认",
            )

            CustomerAssistantLedger(repository).apply_worker_results(
                int(assistant_session["id"]),
                int(run["id"]),
                [completed],
            )
            actions = repository.list_proposed_actions(int(assistant_session["id"]))

            self.assertEqual(actions[0]["status"], "PENDING")
            self.assertEqual(actions[0]["action_type"], "submit_refund")
            self.assertEqual(actions[0]["payload"]["orderNo"], "TK-100")

    def test_async_worker_timeout_persists_terminal_worker_events(self) -> None:
        with _session() as session:
            factory = sessionmaker(bind=session.get_bind(), autoflush=False, autocommit=False, expire_on_commit=False)
            workers = {"stub_qa": _SlowWorker()}
            service = CustomerAssistantService(
                CustomerAssistantRepository(session),
                scheduler=LocalWorkerScheduler(workers),
                async_worker_runtime=CustomerAssistantWorkerRuntime(
                    workers=workers,
                    session_factory=factory,
                    wait_deadline_seconds=0.05,
                    task_timeout_seconds=0.01,
                ),
                worker_profiles=_legacy_stub_baggage_profiles(),
            )
            assistant_session = service.create_session()

            result = service.handle_turn(int(assistant_session["id"]), "行李额度是多少", "timeout-1")
            refs = result["taskSummaries"][0]["workerAsyncRefs"]
            worker_run = _wait_for_worker_run_status(service, refs["workerRunId"], {"TIMED_OUT"})
            refreshed = service.refresh_worker_results(int(assistant_session["id"]))
            worker_events = service.list_worker_events(refs["workerRunId"])["list"]

            self.assertEqual(worker_run["status"], "TIMED_OUT")
            self.assertEqual(refreshed["tasks"][0]["status"], "FAILED")
            event_types = [event["type"] for event in worker_events]
            self.assertIn("worker_timeout_started", event_types)
            self.assertIn("worker_timed_out", event_types)
            self.assertIn("worker_run_timed_out", event_types)

    def test_chatflow_sop_timeout_records_cancellation_unsupported_evidence(self) -> None:
        with _session() as session:
            factory = sessionmaker(bind=session.get_bind(), autoflush=False, autocommit=False, expire_on_commit=False)
            workers = {"chatflow_sop": _SlowWorker()}
            service = CustomerAssistantService(
                CustomerAssistantRepository(session),
                scheduler=LocalWorkerScheduler(workers),
                async_worker_runtime=CustomerAssistantWorkerRuntime(
                    workers=workers,
                    session_factory=factory,
                    async_worker_types={"chatflow_sop"},
                    wait_deadline_seconds=0.05,
                    task_timeout_seconds=0.01,
                ),
            )
            assistant_session = service.create_session()

            result = service.handle_turn(int(assistant_session["id"]), "我要退票", "timeout-chatflow-1")
            summary = result["taskSummaries"][0]
            refs = summary["workerAsyncRefs"]
            _wait_for_worker_run_status(service, refs["workerRunId"], {"TIMED_OUT"})
            refreshed = service.refresh_worker_results(int(assistant_session["id"]))
            failed_task = refreshed["tasks"][0]
            worker_events = service.list_worker_events(refs["workerRunId"])["list"]

            self.assertIn(summary["status"], {"RUNNING", "FAILED"})
            self.assertEqual(failed_task["status"], "FAILED")
            self.assertEqual(failed_task["lastResult"]["evidence"]["chatflowCancellation"]["supported"], False)
            event_types = [event["type"] for event in worker_events]
            self.assertIn("chatflow_v2_cancel_unsupported", event_types)

    def test_async_worker_returns_pending_then_refresh_consumes_completed_result(self) -> None:
        with _session() as session:
            factory = sessionmaker(bind=session.get_bind(), autoflush=False, autocommit=False, expire_on_commit=False)
            workers = {"stub_qa": _SlowWorker(sleep_seconds=1.0)}
            service = CustomerAssistantService(
                CustomerAssistantRepository(session),
                scheduler=LocalWorkerScheduler(workers),
                async_worker_runtime=CustomerAssistantWorkerRuntime(
                    workers=workers,
                    session_factory=factory,
                    wait_deadline_seconds=0.01,
                    task_timeout_seconds=3.0,
                ),
                worker_profiles=_legacy_stub_baggage_profiles(),
            )
            assistant_session = service.create_session()

            started_at = time.monotonic()
            result = service.handle_turn(int(assistant_session["id"]), "行李额度是多少", "pending-1")
            elapsed = time.monotonic() - started_at
            refs = result["taskSummaries"][0]["workerAsyncRefs"]
            worker_run = service.get_worker_run(refs["workerRunId"])

            time.sleep(1.1)
            refreshed = service.refresh_worker_results(int(assistant_session["id"]))

            self.assertLess(elapsed, 0.9)
            self.assertEqual(result["taskSummaries"][0]["status"], "RUNNING")
            self.assertEqual(worker_run["status"], "RUNNING")
            self.assertIn("required worker evidence is pending", " ".join(result["warnings"]))
            self.assertEqual(refreshed["consumed"], 1)
            self.assertEqual(refreshed["tasks"][0]["status"], "COMPLETED")
            self.assertIn("手提行李", refreshed["tasks"][0]["lastResult"]["customerReplyDraft"])

    def test_async_worker_default_deadline_returns_pending_refs_for_slow_worker(self) -> None:
        with _session() as session:
            factory = sessionmaker(bind=session.get_bind(), autoflush=False, autocommit=False, expire_on_commit=False)
            workers = {"stub_qa": _SlowWorker(sleep_seconds=0.45)}
            service = CustomerAssistantService(
                CustomerAssistantRepository(session),
                scheduler=LocalWorkerScheduler(workers),
                async_worker_runtime=CustomerAssistantWorkerRuntime(
                    workers=workers,
                    session_factory=factory,
                    task_timeout_seconds=1.0,
                ),
                worker_profiles=_legacy_stub_baggage_profiles(),
            )
            assistant_session = service.create_session()

            started_at = time.monotonic()
            result = service.handle_turn(int(assistant_session["id"]), "行李额度是多少", "default-pending-1")
            elapsed = time.monotonic() - started_at
            summary = result["taskSummaries"][0]
            refs = summary["workerAsyncRefs"]
            worker_run = service.get_worker_run(refs["workerRunId"])

            self.assertLess(elapsed, 0.3)
            self.assertEqual(summary["status"], "RUNNING")
            self.assertTrue(refs["supported"])
            self.assertTrue(refs["workerRunId"].startswith("customer-assistant-worker-run-"))
            self.assertEqual(worker_run["status"], "RUNNING")
            self.assertIn("required worker evidence is pending", " ".join(result["warnings"]))

            time.sleep(0.5)

    def test_async_workers_are_batch_started_before_join_deadline(self) -> None:
        with _session() as session:
            factory = sessionmaker(bind=session.get_bind(), autoflush=False, autocommit=False, expire_on_commit=False)
            probe = _BatchStartProbe(expected=2)
            workers = {
                "chatflow_sop": _BatchStartWorker(probe),
                "stub_qa": _BatchStartWorker(probe),
            }
            service = CustomerAssistantService(
                CustomerAssistantRepository(session),
                scheduler=LocalWorkerScheduler(workers),
                async_worker_runtime=CustomerAssistantWorkerRuntime(
                    workers=workers,
                    session_factory=factory,
                    async_worker_types={"chatflow_sop", "stub_qa"},
                    wait_deadline_seconds=0.08,
                    task_timeout_seconds=1.0,
                    max_concurrency=2,
                ),
            )
            assistant_session = service.create_session()

            result = service.handle_turn(int(assistant_session["id"]), "我要退票，也想问行李额", "fanout-batch-start-1")
            starts = probe.started_at_by_task()
            start_gap = abs(starts["refund_ticket"] - starts["baggage_qa"])
            summaries = {summary["taskKey"]: summary for summary in result["taskSummaries"]}

            self.assertEqual(set(starts), {"refund_ticket", "baggage_qa"})
            self.assertLess(start_gap, 0.05)
            self.assertEqual(summaries["refund_ticket"]["status"], "RUNNING")
            self.assertEqual(summaries["baggage_qa"]["status"], "RUNNING")
            self.assertTrue(summaries["refund_ticket"]["workerAsyncRefs"]["supported"])
            self.assertTrue(summaries["baggage_qa"]["workerAsyncRefs"]["supported"])

            time.sleep(0.2)

    def test_async_worker_waiting_prompt_becomes_customer_draft(self) -> None:
        with _session() as session:
            factory = sessionmaker(bind=session.get_bind(), autoflush=False, autocommit=False, expire_on_commit=False)
            workers = {"stub_qa": _WaitingWorker()}
            service = CustomerAssistantService(
                CustomerAssistantRepository(session),
                scheduler=LocalWorkerScheduler(workers),
                async_worker_runtime=CustomerAssistantWorkerRuntime(
                    workers=workers,
                    session_factory=factory,
                    wait_deadline_seconds=0.05,
                ),
                worker_profiles=_legacy_stub_baggage_profiles(),
            )
            assistant_session = service.create_session()

            result = service.handle_turn(int(assistant_session["id"]), "行李额度是多少", "waiting-1")

            self.assertEqual(result["taskSummaries"][0]["status"], "WAITING")
            self.assertEqual(result["customerReplyDraft"], "请提供客票舱位和航司。")
            self.assertIn("需要客户补充舱位", result["operatorRecommendation"])


def _task(
    task_id: int,
    task_key: str,
    worker_type: str,
    worker_ref: str,
    checkpoint: dict | None = None,
) -> TaskItem:
    return TaskItem(
        id=task_id,
        session_id=3,
        task_key=task_key,
        task_type="REFUND" if task_key == "refund_ticket" else "QA",
        business_key=task_key,
        short_id=task_key[:4].upper(),
        status=TaskStatus.WAITING if checkpoint else TaskStatus.PENDING,
        worker_type=worker_type,
        worker_ref=worker_ref,
        checkpoint=checkpoint or {},
    )


def _legacy_stub_baggage_profiles() -> CustomerAssistantWorkerProfileCatalog:
    return CustomerAssistantWorkerProfileCatalog.from_json(
        json.dumps(
            {
                "profiles": [
                    {
                        "profileId": "legacy_baggage_stub",
                        "taskKey": "baggage_qa",
                        "taskType": "QA",
                        "workerType": "stub_qa",
                        "workerRef": "baggage_allowance",
                        "modelPolicyRef": "legacy_stub_qa_model",
                        "promptRef": "baggage_allowance_prompt",
                        "riskPolicyRef": "read_only",
                    }
                ]
            }
        )
    )


def _wait_for_worker_run_status(
    service: CustomerAssistantService,
    worker_run_id: str,
    expected_statuses: set[str],
    *,
    timeout_seconds: float = 2.0,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    last: dict[str, object] | None = None
    while time.monotonic() < deadline:
        last = service.get_worker_run(worker_run_id)
        if str(last["status"]) in expected_statuses:
            return last
        time.sleep(0.02)
    raise AssertionError(f"worker run {worker_run_id} did not reach {expected_statuses}; last={last}")


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session("customer_assistant_workers", tables=customer_assistant_tables(), register=register_customer_assistant_tables) as session:
        yield session


class _SlowWorker:
    def __init__(self, sleep_seconds: float = 0.1) -> None:
        self._sleep_seconds = sleep_seconds

    def run(self, task: TaskItem, message: str) -> WorkerResult:
        time.sleep(self._sleep_seconds)
        return WorkerResult(
            task_id=int(task.id or 0),
            worker_type=task.worker_type,
            status=TaskStatus.COMPLETED,
            customer_reply_draft="经济舱通常可免费携带一件手提行李，托运行李额以客票规则和航司政策为准。",
        )


class _BatchStartProbe:
    def __init__(self, expected: int) -> None:
        self._expected = expected
        self._lock = threading.Lock()
        self._started_at_by_task: dict[str, float] = {}
        self.all_started = threading.Event()

    def record_started(self, task_key: str) -> None:
        with self._lock:
            self._started_at_by_task.setdefault(task_key, time.monotonic())
            if len(self._started_at_by_task) >= self._expected:
                self.all_started.set()

    def started_at_by_task(self) -> dict[str, float]:
        with self._lock:
            return dict(self._started_at_by_task)


class _BatchStartWorker:
    def __init__(self, probe: _BatchStartProbe) -> None:
        self._probe = probe

    def run(self, task: TaskItem, message: str) -> WorkerResult:
        self._probe.record_started(task.task_key)
        self._probe.all_started.wait(timeout=1.0)
        time.sleep(0.12)
        return WorkerResult(
            task_id=int(task.id or 0),
            worker_type=task.worker_type,
            status=TaskStatus.COMPLETED,
            operator_recommendation=f"completed {task.task_key}: {message}",
            customer_reply_draft=f"completed {task.task_key}",
        )


class _WaitingWorker:
    def run(self, task: TaskItem, message: str) -> WorkerResult:
        return WorkerResult(
            task_id=int(task.id or 0),
            worker_type=task.worker_type,
            status=TaskStatus.WAITING,
            operator_recommendation="需要客户补充舱位后再判断行李额。",
            customer_reply_draft="请提供客票舱位和航司。",
            missing_fields=["客票舱位", "航司"],
        )


if __name__ == "__main__":
    unittest.main()
