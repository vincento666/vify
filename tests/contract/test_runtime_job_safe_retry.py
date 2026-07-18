import time
import unittest
from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.database import get_session_factory
from app.main import app
from app.modules.workflow.infra.repository import WorkflowRepository
from app.modules.runtime.infra.runtime_job_repository import RuntimeJobRepository
from app.modules.workflow.runtime_job_worker import build_workflow_runtime_job_worker


class RuntimeJobSafeRetryTest(unittest.TestCase):
    def test_worker_continues_after_completed_node_without_duplicate_node_run(self) -> None:
        with TestClient(app) as client, patch("app.modules.workflow.web.router.threading.Thread"):
            workflow = _create_three_node_workflow(client)
            version = client.post(f"/api/v1/workflows/{workflow['id']}/publish").json()["data"]
            started_response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={
                    "input": {"sys.query": "safe retry"},
                    "versionId": version["id"],
                    "idempotencyKey": f"safe-retry-{time.time_ns()}",
                },
            )
            self.assertEqual(started_response.status_code, 200, started_response.text)
            started = started_response.json()["data"]
            run_id = int(started["runId"])

            with get_session_factory()() as session:
                repository = WorkflowRepository(session)
                node_run_id = repository.create_node_run(run_id, "message_1", "MESSAGE", inputs={"sys.query": "safe retry"})
                repository.finish_node_run(node_run_id, "COMPLETED", {"content": "first"})
                worker = build_workflow_runtime_job_worker(session, worker_id="safe-retry-worker")
                job = RuntimeJobRepository(session).get_by_run(run_id)
                self.assertIsNotNone(job)
                worker_result = worker.run_once(int(job["id"]))

            result = _wait_for_result(client, started["resultRef"])
            nodes = client.get(started["nodesRef"]).json()["data"]["list"]

        self.assertTrue(worker_result["claimed"])
        self.assertEqual(worker_result["status"], "COMPLETED")
        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(result["output"], {"final": "first second"})
        self.assertEqual(
            [node["nodeKey"] for node in nodes],
            ["message_1", "message_2", "end"],
        )
        self.assertEqual([node["nodeKey"] for node in nodes].count("message_1"), 1)


def _wait_for_result(client: TestClient, result_ref: str, timeout: float = 5.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        latest = client.get(result_ref).json()["data"]
        if latest["status"] in {"SUCCEEDED", "FAILED", "INTERRUPTED", "CANCELLED"}:
            return latest
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for terminal result; latest={latest}")


def _create_three_node_workflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Runtime Job Safe Retry {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "message_1",
                    "type": "MESSAGE",
                    "name": "Message 1",
                    "config": {"content": "first", "outputVariable": "content"},
                },
                {
                    "nodeKey": "message_2",
                    "type": "MESSAGE",
                    "name": "Message 2",
                    "config": {"content": "{{message_1.content}} second", "outputVariable": "content"},
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{message_2.content}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "message_1", "condition": None},
                {"sourceNodeKey": "message_1", "targetNodeKey": "message_2", "condition": None},
                {"sourceNodeKey": "message_2", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
