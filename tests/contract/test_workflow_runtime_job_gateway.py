import time
import unittest
from datetime import datetime

import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory
from app.main import app


class WorkflowRuntimeJobGatewayTest(unittest.TestCase):
    def test_workflow_run_gateway_persists_and_completes_runtime_job(self) -> None:
        with TestClient(app) as client:
            workflow = _create_workflow(client, message="job gateway")
            version = client.post(f"/api/v1/workflows/{workflow['id']}/publish").json()["data"]
            started = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={
                    "input": {"sys.query": "job gateway"},
                    "versionId": version["id"],
                    "idempotencyKey": f"runtime-job-{time.time_ns()}",
                },
            )
            self.assertEqual(started.status_code, 200, started.text)
            data = started.json()["data"]
            terminal = _wait_for_result(client, data["resultRef"])

        self.assertEqual(terminal["status"], "SUCCEEDED")
        job = _runtime_job_for_run(int(data["runId"]))
        self.assertEqual(job["run_id"], data["runId"])
        self.assertEqual(job["owner_type"], "WORKFLOW")
        self.assertEqual(job["owner_id"], workflow["id"])
        self.assertEqual(job["job_type"], "runtime_v2_completion")
        self.assertEqual(job["status"], "COMPLETED")
        self.assertEqual(job["attempt_count"], 1)
        self.assertTrue(str(job["lease_owner"]).startswith("inline-runtime-v2-"))
        self.assertIsNotNone(job["started_at"])
        self.assertIsNotNone(job["finished_at"])


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
            "name": f"Runtime Job Gateway {datetime.now().timestamp()}",
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
