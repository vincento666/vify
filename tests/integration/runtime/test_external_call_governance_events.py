from __future__ import annotations

import time
from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app


def test_runtime_v2_external_call_failure_emits_governance_event() -> None:
    with TestClient(app) as client:
        workflow = _create_invalid_llm_workflow(client)
        started_response = client.post(
            f"/api/v1/workflows/{workflow['id']}/runs",
            json={"input": {"sys.query": "governance"}},
        )
        assert started_response.status_code == 200, started_response.text
        started = started_response.json()["data"]
        run_id = int(started["runId"])

        failed = _wait_for_run_status(client, run_id, "FAILED")
        events = client.get(f"/api/v1/runtime-runs/{run_id}/events").json()["data"]["list"]

    external_event = next(event for event in events if event["type"] == "workflow_node_external_call_failed")
    payload = external_event["payload"]
    assert failed["status"] == "FAILED"
    assert payload["callType"] == "LLM"
    assert payload["nodeKey"] == "llm_1"
    assert payload["nodeType"] == "LLM"
    assert payload["errorKind"] == "provider_error"
    assert payload["attempts"] == 2
    assert payload["retryCount"] == 1
    assert payload["timeoutMs"] == 50
    assert payload["breakerOpen"] is True
    assert "workflow_node_failed" in [event["type"] for event in events]


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


def _create_invalid_llm_workflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"External Call Governance Runtime {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "llm_1",
                    "type": "LLM",
                    "name": "LLM",
                    "config": {
                        "modelConfigId": 987654321,
                        "prompt": "reply to {{start.sys.query}}",
                        "outputVariable": "answer",
                        "timeoutMs": 50,
                        "retryCount": 1,
                        "breakerFailureThreshold": 2,
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{llm_1.answer}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "llm_1", "condition": None},
                {"sourceNodeKey": "llm_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]
