import time
import unittest
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import get_session
from app.main import app
from app.modules.customer_assistant.domain.models import TaskItem, TaskStatus
from app.modules.customer_assistant.domain.workers import ChatflowSopWorker
from app.modules.customer_assistant.web.router import build_customer_assistant_service, _customer_assistant_sop_adapter
from app.modules.workflow.infra.runtime_job_repository import RuntimeJobRepository


class CustomerAssistantWorkerDefaultAsyncRefsTest(unittest.TestCase):
    def test_bound_chatflow_sop_worker_defaults_to_async_refs_and_queues_runtime_job(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_message_chatflow(client, content="213.4 async default done")
            with _session() as session:
                service = build_customer_assistant_service(
                    session,
                    Settings(runtime_lab_sop_chatflow_ids=f"refund_ticket:{chatflow['id']}"),
                )
                assistant_session = service.create_session()

                turn = service.handle_turn(
                    int(assistant_session["id"]),
                    "我要退票",
                    f"2134-default-async-{time.time_ns()}",
                )
                summary = next(task for task in turn["taskSummaries"] if task["taskKey"] == "refund_ticket")
                last_result = summary["lastResult"]
                evidence = last_result["evidence"]
                runtime_refs = evidence["runtimeRefs"]
                worker_refs = summary["workerAsyncRefs"]
                job = RuntimeJobRepository(session).get_by_run(int(runtime_refs["runId"]))

        self.assertEqual(summary["status"], "WAITING")
        self.assertEqual(last_result["status"], "WAITING")
        self.assertTrue(worker_refs["supported"])
        self.assertTrue(worker_refs["workerRunId"].startswith("customer-assistant-worker-run-"))
        self.assertEqual(evidence["runtimeVersion"], 2)
        self.assertEqual(evidence["chatflowRuntimeRefs"], runtime_refs)
        self.assertEqual(turn["chatflowSession"]["status"], "WAITING")
        self.assertEqual(turn["chatflowSession"]["runId"], runtime_refs["runId"])
        self.assertIn("/api/v1/runtime-runs/", turn["chatflowSession"]["eventStreamRef"])
        self.assertIsNotNone(job)
        assert job is not None
        self.assertEqual(job["owner_type"], "CHATFLOW")
        self.assertEqual(job["status"], "QUEUED")
        self.assertIn("等待 Chatflow runtime", evidence["blockingReason"])
        self.assertIn("事件流", evidence["operatorAdvice"])

    def test_explicit_sync_fallback_completes_without_background_runtime_job(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_message_chatflow(client, content="213.4 explicit sync fallback done")
            with _session() as session:
                service = build_customer_assistant_service(
                    session,
                    Settings(
                        runtime_lab_sop_chatflow_ids=f"refund_ticket:{chatflow['id']}",
                        customer_assistant_sop_runtime_invocation_mode="sync",
                    ),
                )
                assistant_session = service.create_session()

                turn = service.handle_turn(
                    int(assistant_session["id"]),
                    "我要退票",
                    f"2134-explicit-sync-{time.time_ns()}",
                )
                summary = next(task for task in turn["taskSummaries"] if task["taskKey"] == "refund_ticket")
                last_result = summary["lastResult"]
                evidence = last_result["evidence"]
                runtime_refs = evidence["runtimeRefs"]
                job = RuntimeJobRepository(session).get_by_run(int(runtime_refs["runId"]))

        self.assertEqual(summary["status"], "COMPLETED")
        self.assertEqual(last_result["status"], "COMPLETED")
        self.assertEqual(evidence["runtimeVersion"], 2)
        self.assertEqual(turn["chatflowSession"]["status"], "COMPLETED")
        self.assertIsNone(job)

    def test_followup_before_background_job_finishes_preserves_runtime_v2_refs(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_message_chatflow(client, content="213.4 pending resume still v2")
            with _session() as session:
                worker = ChatflowSopWorker(
                    _customer_assistant_sop_adapter(
                        session,
                        {"refund_ticket": int(chatflow["id"])},
                        runtime_invocation_mode="async",
                    )
                )
                first = worker.run(
                    _task(task_id=213401, session_id=2134, task_key="refund_ticket", worker_ref="refund_ticket"),
                    "我要退票",
                )
                second = worker.run(
                    _task(
                        task_id=213401,
                        session_id=2134,
                        task_key="refund_ticket",
                        worker_ref="refund_ticket",
                        checkpoint=first.checkpoint,
                    ),
                    "订单号 TK2134",
                )

        self.assertEqual(first.status, TaskStatus.WAITING)
        self.assertIn(second.status, {TaskStatus.WAITING, TaskStatus.COMPLETED})
        self.assertEqual(second.evidence["runtimeVersion"], 2)
        self.assertEqual(
            second.evidence["chatflowSession"]["runId"],
            first.evidence["chatflowSession"]["runId"],
        )
        self.assertNotEqual(second.status, TaskStatus.FAILED)


@contextmanager
def _session() -> Iterator[Session]:
    yield from get_session()


def _create_message_chatflow(client: TestClient, *, content: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"213.4 Customer Assistant Async Default {time.time_ns()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "middle_1",
                    "type": "MESSAGE",
                    "name": "Middle",
                    "config": {"content": content, "outputVariable": "content"},
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{middle_1.content}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "middle_1", "condition": None},
                {"sourceNodeKey": "middle_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _task(
    *,
    task_id: int,
    session_id: int,
    task_key: str,
    worker_ref: str,
    checkpoint: dict[str, object] | None = None,
) -> TaskItem:
    return TaskItem(
        id=task_id,
        session_id=session_id,
        task_key=task_key,
        task_type="sop",
        business_key=task_key,
        short_id=f"T{task_id}",
        status=TaskStatus.PENDING,
        worker_type="chatflow_sop",
        worker_ref=worker_ref,
        checkpoint=dict(checkpoint or {}),
        input_snapshot={},
    )
