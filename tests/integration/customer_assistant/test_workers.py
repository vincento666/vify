import unittest
import tempfile
import time
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.modules.customer_assistant.domain.ledger import CustomerAssistantLedger
from app.modules.customer_assistant.domain.models import TaskItem, TaskStatus, WorkerResult
from app.modules.customer_assistant.domain.scheduler import LocalWorkerScheduler
from app.modules.customer_assistant.domain.service import CustomerAssistantService
from app.modules.customer_assistant.domain.worker_runtime import CustomerAssistantWorkerRuntime
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
            )
            assistant_session = service.create_session()

            result = service.handle_turn(int(assistant_session["id"]), "行李额度是多少", "timeout-1")
            refs = result["taskSummaries"][0]["workerAsyncRefs"]
            worker_run = service.get_worker_run(refs["workerRunId"])
            worker_events = service.list_worker_events(refs["workerRunId"])["list"]

            self.assertEqual(worker_run["status"], "TIMED_OUT")
            self.assertEqual(result["taskSummaries"][0]["status"], "FAILED")
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
            worker_events = service.list_worker_events(refs["workerRunId"])["list"]

            self.assertEqual(summary["status"], "FAILED")
            self.assertEqual(summary["lastResult"]["evidence"]["chatflowCancellation"]["supported"], False)
            event_types = [event["type"] for event in worker_events]
            self.assertIn("chatflow_v2_cancel_unsupported", event_types)

    def test_async_worker_returns_pending_then_refresh_consumes_completed_result(self) -> None:
        with _session() as session:
            factory = sessionmaker(bind=session.get_bind(), autoflush=False, autocommit=False, expire_on_commit=False)
            workers = {"stub_qa": _SlowWorker(sleep_seconds=0.12)}
            service = CustomerAssistantService(
                CustomerAssistantRepository(session),
                scheduler=LocalWorkerScheduler(workers),
                async_worker_runtime=CustomerAssistantWorkerRuntime(
                    workers=workers,
                    session_factory=factory,
                    wait_deadline_seconds=0.01,
                    task_timeout_seconds=1.0,
                ),
            )
            assistant_session = service.create_session()

            started_at = time.monotonic()
            result = service.handle_turn(int(assistant_session["id"]), "行李额度是多少", "pending-1")
            elapsed = time.monotonic() - started_at
            refs = result["taskSummaries"][0]["workerAsyncRefs"]
            worker_run = service.get_worker_run(refs["workerRunId"])

            time.sleep(0.18)
            refreshed = service.refresh_worker_results(int(assistant_session["id"]))

            self.assertLess(elapsed, 0.08)
            self.assertEqual(result["taskSummaries"][0]["status"], "RUNNING")
            self.assertEqual(worker_run["status"], "RUNNING")
            self.assertIn("required worker evidence is pending", " ".join(result["warnings"]))
            self.assertEqual(refreshed["consumed"], 1)
            self.assertEqual(refreshed["tasks"][0]["status"], "COMPLETED")
            self.assertIn("手提行李", refreshed["tasks"][0]["lastResult"]["customerReplyDraft"])

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


def _session() -> Session:
    tmp_dir = tempfile.TemporaryDirectory()
    db_path = Path(tmp_dir.name) / "customer_assistant_workers.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    register_customer_assistant_tables()
    Base.metadata.create_all(bind=engine, tables=customer_assistant_tables())
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = factory()
    session.info["_tmp_dir"] = tmp_dir
    return session


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
