import time
import unittest
from datetime import datetime
from unittest.mock import patch

import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory
from app.main import app
from app.modules.workflow.runtime_job_worker import build_workflow_runtime_job_worker


class RuntimeJobWorkerGatewayTest(unittest.TestCase):
    def test_standalone_worker_completes_workflow_run_when_inline_thread_is_disabled(self) -> None:
        with TestClient(app) as client, patch("app.modules.workflow.web.router.threading.Thread"):
            workflow = _create_workflow(client, message="standalone worker")
            version = client.post(f"/api/v1/workflows/{workflow['id']}/publish").json()["data"]
            started_response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={
                    "input": {"sys.query": "worker"},
                    "versionId": version["id"],
                    "idempotencyKey": f"runtime-worker-{time.time_ns()}",
                },
            )
            self.assertEqual(started_response.status_code, 200, started_response.text)
            started = started_response.json()["data"]
            before_worker = client.get(started["resultRef"]).json()["data"]

            self.assertEqual(before_worker["status"], "RUNNING")
            queued_job = _runtime_job_for_run(int(started["runId"]))
            self.assertEqual(queued_job["status"], "QUEUED")

            with get_session_factory()() as session:
                worker = build_workflow_runtime_job_worker(session, worker_id="contract-worker")
                worker_result = worker.run_once(job_id=int(queued_job["id"]))

            after_worker = _wait_for_result(client, started["resultRef"])

        self.assertTrue(worker_result["claimed"])
        self.assertEqual(worker_result["status"], "COMPLETED")
        self.assertEqual(after_worker["status"], "SUCCEEDED")
        self.assertEqual(after_worker["output"], {"final": "standalone worker"})
        completed_job = _runtime_job_for_run(int(started["runId"]))
        self.assertEqual(completed_job["status"], "COMPLETED")
        self.assertEqual(completed_job["lease_owner"], "contract-worker")


def _wait_for_result(client: TestClient, result_ref: str, timeout: float = 5.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        latest = client.get(result_ref).json()["data"]
        if latest["status"] in {"SUCCEEDED", "FAILED", "INTERRUPTED", "CANCELLED"}:
            return latest
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for terminal result; latest={latest}")


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


def _create_workflow(client: TestClient, *, message: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Runtime Job Worker {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "message_1",
                    "type": "MESSAGE",
                    "name": "Message",
                    "config": {"content": message, "outputVariable": "content"},
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


if __name__ == "__main__":
    unittest.main()
