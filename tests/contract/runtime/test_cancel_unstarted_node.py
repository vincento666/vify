from __future__ import annotations

import time
import unittest
from datetime import datetime
from unittest.mock import patch

import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.database import Base, get_session_factory
from app.main import app


class RuntimeV2CancelUnstartedNodeContractTest(unittest.TestCase):
    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_settings, None)

    def test_cancel_queued_run_cancels_job_and_starts_no_nodes(self) -> None:
        app.dependency_overrides[get_settings] = lambda: Settings(
            _env_file=None,
            runtime_v2_request_thread_completion_enabled=False,
        )
        with TestClient(app) as client, patch("app.modules.workflow.web.router.threading.Thread") as thread_cls:
            workflow = _create_workflow(client)
            started = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"sys.query": "queued"}, "idempotencyKey": f"cancel-queued-{time.time_ns()}"},
            )
            self.assertEqual(started.status_code, 200, started.text)
            run_id = int(started.json()["data"]["runId"])

            cancelled = client.post(
                f"/api/v1/runtime-runs/{run_id}/cancel",
                json={"deadlineMs": 500, "reason": "operator cancelled queued run"},
            )
            self.assertEqual(cancelled.status_code, 200, cancelled.text)
            result = client.get(f"/api/v1/runtime-runs/{run_id}/result").json()["data"]
            nodes = client.get(f"/api/v1/runtime-runs/{run_id}/nodes").json()["data"]["list"]
            job = _runtime_job_for_run(run_id)

        thread_cls.assert_not_called()
        self.assertEqual(cancelled.json()["data"]["status"], "CANCELLED")
        self.assertEqual(cancelled.json()["data"]["cancellation"]["phase"], "queued")
        self.assertEqual(cancelled.json()["data"]["cancellation"]["deadlineMs"], 500)
        self.assertEqual(result["status"], "CANCELLED")
        self.assertEqual(nodes, [])
        self.assertEqual(job["status"], "CANCELLED")
        self.assertEqual(job["last_error"], "operator cancelled queued run")


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


def _create_workflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Cancel Queued Runtime {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "message_1",
                    "type": "MESSAGE",
                    "name": "Message",
                    "config": {"content": "queued {{start.sys.query}}", "outputVariable": "content"},
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
