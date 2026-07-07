from __future__ import annotations

import time
from typing import Any

from fastapi.testclient import TestClient

from app.main import app


def test_run_completion_uses_active_path_and_persists_join_selection_state() -> None:
    with TestClient(app) as client:
        workflow = _create_workflow(client)
        started = client.post(
            f"/api/v1/workflows/{workflow['id']}/runs",
            json={"input": {"sys.query": "vip"}},
        )
        assert started.status_code == 200, started.text
        run = started.json()["data"]
        terminal = _wait_for_result(client, run["resultRef"])
        nodes = client.get(run["nodesRef"]).json()["data"]["list"]

    assert terminal["status"] == "SUCCEEDED"
    assert terminal["output"] == {"final": "VIP vip"}
    assert [node["nodeKey"] for node in nodes] == ["router", "vip_message", "join"]
    join_state = next(node["selectionState"] for node in nodes if node["nodeKey"] == "join")
    assert join_state["state"] == "completed"
    assert join_state["selectedUpstreamNodeKeys"] == ["vip_message"]
    assert join_state["skippedUpstreamNodeKeys"] == ["fallback_message"]
    assert join_state["reason"] == "implicit join waits only for selected upstreams"


def _create_workflow(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Runtime V2 Active Path Completion {time.time_ns()}",
            "description": "spec 215.4 active path completion fixture",
            "nodes": [
                _node(
                    "start",
                    "START",
                    {"ports": [{"key": "default", "allowFanOut": False}]},
                ),
                _node(
                    "router",
                    "CONDITION",
                    {
                        "expression": "vip",
                        "branches": [{"key": "vip"}],
                    },
                ),
                _node("vip_message", "MESSAGE", {"content": "VIP {{start.sys.query}}", "outputVariable": "answer"}),
                _node("fallback_message", "MESSAGE", {"content": "fallback", "outputVariable": "answer"}),
                _node("join", "END", {"outputVariable": "final", "output": "{{vip_message.answer}}"}),
            ],
            "edges": [
                _edge("start", "router"),
                _edge("router", "vip_message", "vip"),
                _edge("router", "fallback_message"),
                _edge("vip_message", "join"),
                _edge("fallback_message", "join"),
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


def _node(node_key: str, node_type: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"nodeKey": node_key, "type": node_type, "name": node_key, "config": config or {}}


def _edge(source: str, target: str, condition: str | None = None) -> dict[str, Any]:
    return {"sourceNodeKey": source, "targetNodeKey": target, "condition": condition}
