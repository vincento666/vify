from __future__ import annotations

import time
from datetime import datetime

from fastapi.testclient import TestClient

from app.core.database import get_session_factory
from app.main import app
from app.modules.workflow.infra.repository import WorkflowRepository


def test_running_node_cancel_stops_downstream_scheduling_and_marks_node_cancelled() -> None:
    with TestClient(app) as client:
        workflow = _create_slow_code_workflow(client)
        started_response = client.post(
            f"/api/v1/workflows/{workflow['id']}/runs",
            json={"input": {"sys.query": "cancel-running"}},
        )
        assert started_response.status_code == 200, started_response.text
        started = started_response.json()["data"]
        run_id = int(started["runId"])

        _wait_for_node_status(run_id, "code_1", "RUNNING")
        cancelled = client.post(
            f"/api/v1/runtime-runs/{run_id}/cancel",
            json={"deadlineMs": 1500, "reason": "operator cancelled running code"},
        )
        assert cancelled.status_code == 200, cancelled.text
        _wait_for_run_status(client, run_id, "CANCELLED")
        time.sleep(0.8)

        result = client.get(f"/api/v1/runtime-runs/{run_id}/result").json()["data"]
        nodes = client.get(f"/api/v1/runtime-runs/{run_id}/nodes").json()["data"]["list"]
        events = client.get(f"/api/v1/runtime-runs/{run_id}/events").json()["data"]["list"]

    by_key = {node["nodeKey"]: node for node in nodes}
    code_events = [event for event in events if event.get("nodeId") == "code_1"]

    assert cancelled.json()["data"]["cancellation"]["phase"] == "running"
    assert cancelled.json()["data"]["cancellation"]["deadlineMs"] == 1500
    assert result["status"] == "CANCELLED"
    assert by_key["code_1"]["status"] == "CANCELLED"
    assert "end" not in by_key
    assert "workflow_node_cancelled" in [event["type"] for event in code_events]
    assert "workflow_node_completed" not in [event["type"] for event in code_events]
    assert "workflow_run_completed" not in [event["type"] for event in events]


def _wait_for_node_status(run_id: int, node_key: str, status: str, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    latest: list[dict[str, object]] = []
    while time.monotonic() < deadline:
        with get_session_factory()() as session:
            latest = WorkflowRepository(session).list_node_runs(run_id)
        if any(row["node_key"] == node_key and row["status"] == status for row in latest):
            return
        time.sleep(0.05)
    raise AssertionError(f"Timed out waiting for {node_key}={status}; latest={latest}")


def _wait_for_run_status(client: TestClient, run_id: int, status: str, timeout: float = 5.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/runtime-runs/{run_id}/result")
        assert response.status_code == 200, response.text
        latest = response.json()["data"]
        if latest["status"] == status:
            return latest
        time.sleep(0.05)
    raise AssertionError(f"Timed out waiting for run {run_id}={status}; latest={latest}")


def _create_slow_code_workflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Cooperative Cancel Runtime {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "code_1",
                    "type": "CODE",
                    "name": "Slow Code",
                    "config": {
                        "language": "javascript",
                        "timeout": 3,
                        "code": "const end = Date.now() + 650; while (Date.now() < end) {}; result = { value: 'done' }",
                        "outputParameters": [{"name": "value", "type": "string"}],
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{code_1.value}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "code_1", "condition": None},
                {"sourceNodeKey": "code_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]
