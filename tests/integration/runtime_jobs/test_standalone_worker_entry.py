from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory
from app.main import app


class RuntimeJobStandaloneWorkerEntryTest(unittest.TestCase):
    def test_script_once_can_drain_a_specific_runtime_job(self) -> None:
        with TestClient(app) as client, patch("app.modules.workflow.web.router.threading.Thread"):
            workflow = _create_workflow(client, message="standalone script worker")
            started_response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={
                    "input": {"sys.query": "script"},
                    "idempotencyKey": f"standalone-script-{time.time_ns()}",
                },
            )
            self.assertEqual(started_response.status_code, 200, started_response.text)
            started = started_response.json()["data"]
            queued_job = _runtime_job_for_run(int(started["runId"]))

            script_result = _run_worker_script(int(queued_job["id"]))
            terminal = _wait_for_result(client, started["resultRef"])
            completed_job = _runtime_job_for_run(int(started["runId"]))

        self.assertTrue(script_result["claimed"])
        self.assertEqual(script_result["jobId"], int(queued_job["id"]))
        self.assertEqual(script_result["status"], "COMPLETED")
        self.assertEqual(terminal["status"], "SUCCEEDED")
        self.assertEqual(terminal["output"], {"final": "standalone script worker"})
        self.assertEqual(completed_job["lease_owner"], "integration-standalone-worker")


def _run_worker_script(job_id: int) -> dict[str, object]:
    repo_root = Path(__file__).resolve().parents[3]
    script = repo_root / "scripts" / "runtime_job_worker.py"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo_root)
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--once",
            "--owner",
            "workflow",
            "--worker-id",
            "integration-standalone-worker",
            "--job-id",
            str(job_id),
        ],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        raise AssertionError(f"Worker script produced no JSON output; stderr={result.stderr}")
    return json.loads(lines[-1])


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
            "name": f"Standalone Worker Entry {datetime.now().timestamp()}",
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
