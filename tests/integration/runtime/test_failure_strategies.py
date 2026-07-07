from __future__ import annotations

import time
from typing import Any

from fastapi.testclient import TestClient

from app.main import app


def test_partial_failure_strategy_finishes_active_path_with_partial_evidence() -> None:
    with TestClient(app) as client:
        workflow = _create_partial_failure_workflow(client)
        started = client.post(
            f"/api/v1/workflows/{workflow['id']}/runs",
            json={"input": {"sys.query": "partial"}},
        )
        assert started.status_code == 200, started.text
        run = started.json()["data"]
        terminal = _wait_for_result(client, run["resultRef"])
        nodes = client.get(run["nodesRef"]).json()["data"]["list"]

    code_node = next(node for node in nodes if node["nodeKey"] == "code_1")
    assert terminal["status"] == "SUCCEEDED"
    assert terminal["output"]["final"] == "partial=True error=division by zero"
    assert code_node["status"] == "COMPLETED"
    assert code_node["outputs"]["success"] is False
    assert code_node["outputs"]["partialSuccess"] is True
    assert code_node["outputs"]["errorBehavior"] == "partial"
    assert code_node["outputs"]["evidence"]["failureStrategy"] == "partial_success"


def _create_partial_failure_workflow(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Runtime V2 Partial Failure {time.time_ns()}",
            "description": "spec 215.5 partial failure strategy fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "code_1",
                    "type": "CODE",
                    "name": "Partial Code",
                    "config": {
                        "language": "python",
                        "code": "result = 1 / 0",
                        "errorBehavior": "partial",
                        "outputVariable": "answer",
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {
                        "outputVariable": "final",
                        "output": "partial={{code_1.partialSuccess}} error={{code_1.error}}",
                    },
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


def _wait_for_result(client: TestClient, result_ref: str, timeout: float = 5.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    latest: dict[str, Any] = {}
    while time.monotonic() < deadline:
        latest = client.get(result_ref).json()["data"]
        if latest["status"] in {"SUCCEEDED", "FAILED", "INTERRUPTED", "CANCELLED"}:
            return latest
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for terminal result; latest={latest}")
