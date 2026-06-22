import time
import unittest
from collections.abc import Callable
from datetime import datetime
from unittest.mock import patch

import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory
from app.main import app
from app.modules.workflow import runtime_job_worker as runtime_job_worker_module
from app.modules.workflow.infra.realtime.redis_streams import InMemoryRuntimeEventStreamBus
from app.modules.workflow.infra.runtime_job_repository import RuntimeJobRepository


class ChatflowRuntimeJobWorkerGatewayTest(unittest.TestCase):
    def test_standalone_worker_drains_chatflow_runtime_jobs_when_inline_thread_is_disabled(self) -> None:
        worker_factory = getattr(runtime_job_worker_module, "build_chatflow_runtime_job_worker", None)
        self.assertTrue(callable(worker_factory), "Chatflow runtime job worker factory is missing")

        cases: list[tuple[str, Callable[[TestClient], dict[str, object]], str, dict[str, object] | None, str]] = [
            ("completion", _create_message_chatflow, "SUCCEEDED", {"final": "worker says Ada"}, "workflow_run_completed"),
            ("interrupt", _create_question_chatflow, "INTERRUPTED", None, "workflow_run_interrupted"),
            ("failure", _create_failing_message_chatflow, "FAILED", {}, "workflow_run_failed"),
        ]
        with TestClient(app) as client, patch("app.modules.workflow.web.router.threading.Thread"):
            for case_name, create_chatflow, expected_status, expected_output, expected_event_type in cases:
                chatflow = create_chatflow(client)
                started_response = client.post(
                    f"/api/v1/chatflows/{chatflow['id']}/runs-v2",
                    json={
                        "input": {
                            "sys.query": "Ada",
                            "sys.session_id": f"chatflow-worker-{case_name}-{time.time_ns()}",
                            "sys.conversation_id": f"chatflow-worker-{case_name}-{time.time_ns()}",
                            "sys.user_id": "contract-chatflow-worker",
                            "sys.channel": "api",
                        }
                    },
                )
                self.assertEqual(started_response.status_code, 200, started_response.text)
                started = started_response.json()["data"]
                run_id = int(started["runId"])
                before_worker = client.get(started["resultRef"]).json()["data"]
                self.assertEqual(before_worker["status"], "RUNNING", case_name)

                event_stream_bus = InMemoryRuntimeEventStreamBus()
                with get_session_factory()() as session:
                    queued_job = RuntimeJobRepository(session).enqueue(
                        run_id=run_id,
                        owner_type="CHATFLOW",
                        owner_id=int(chatflow["id"]),
                        job_type="runtime_v2_completion",
                        payload={"chatflowId": int(chatflow["id"]), "case": case_name},
                    )
                    self.assertEqual(queued_job["status"], "QUEUED", case_name)
                    worker = worker_factory(
                        session,
                        worker_id=f"chatflow-contract-worker-{case_name}",
                        event_stream_bus=event_stream_bus,
                    )
                    worker_result = worker.run_once(job_id=int(queued_job["id"]))

                terminal = _wait_for_result(client, started["resultRef"], expected_status)
                completed_job = _runtime_job_for_run(run_id)
                stream_events = event_stream_bus.read_after(run_id=run_id, after_sequence=0)

                self.assertTrue(worker_result["claimed"], case_name)
                self.assertEqual(worker_result["status"], "COMPLETED", case_name)
                self.assertEqual(terminal["status"], expected_status, case_name)
                if expected_output is not None:
                    self.assertEqual(terminal["output"], expected_output, case_name)
                self.assertEqual(completed_job["status"], "COMPLETED", case_name)
                self.assertEqual(completed_job["lease_owner"], f"chatflow-contract-worker-{case_name}", case_name)
                self.assertIn(expected_event_type, [event["type"] for event in stream_events], case_name)


def _wait_for_result(
    client: TestClient,
    result_ref: str,
    wanted_status: str,
    timeout: float = 5.0,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(result_ref)
        assert response.status_code == 200, response.text
        latest = response.json()["data"]
        if latest["status"] == wanted_status:
            return latest
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for {wanted_status}; latest={latest}")


def _runtime_job_for_run(run_id: int) -> dict[str, object]:
    job_table = Base.metadata.tables["runtime_jobs"]
    with get_session_factory()() as session:
        row = session.execute(
            sa.select(job_table)
            .where(job_table.c.run_id == run_id, job_table.c.deleted.is_(False))
            .order_by(job_table.c.id.desc())
        ).mappings().first()
    if row is None:
        raise AssertionError(f"No runtime job found for run {run_id}")
    return dict(row)


def _create_message_chatflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Chatflow Runtime Job Worker Completion {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "message_1",
                    "type": "MESSAGE",
                    "name": "Message",
                    "config": {"content": "worker says {{start.sys.query}}", "outputVariable": "content"},
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{message_1.content}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "message_1", "condition": None},
                {"sourceNodeKey": "message_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_question_chatflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Chatflow Runtime Job Worker Interrupt {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "question_1",
                    "type": "QUESTION",
                    "name": "Question",
                    "config": {"question": "Continue?", "outputVariable": "answer", "answerType": "text"},
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "answer={{question_1.answer}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "question_1", "condition": None},
                {"sourceNodeKey": "question_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_failing_message_chatflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Chatflow Runtime Job Worker Failure {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {"nodeKey": "message_1", "type": "MESSAGE", "name": "Message", "config": {"raiseError": "node failed"}},
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final", "output": "done"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "message_1", "condition": None},
                {"sourceNodeKey": "message_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
