from __future__ import annotations

import time
from typing import Any

from fastapi.testclient import TestClient

from app.main import app


def test_side_effect_terminal_leaf_succeeds_without_next_node_error() -> None:
    with TestClient(app) as client:
        workflow = _create_workflow(
            client,
            nodes=[
                _node("start", "START"),
                _node(
                    "notify",
                    "CODE",
                    {
                        "sideEffectTerminal": True,
                        "code": (
                            "result = {"
                            '"sideEffectOnly": True, '
                            '"deliveryStatus": "sent", '
                            '"sideEffectEvidence": {"channel": "ops", "idempotencyKey": "terminal-2154"}'
                            "}"
                        ),
                    },
                ),
                _node("end", "END"),
            ],
            edges=[_edge("start", "notify")],
        )
        started = client.post(
            f"/api/v1/workflows/{workflow['id']}/runs",
            json={"input": {"sys.query": "side-effect terminal"}},
        )
        assert started.status_code == 200, started.text
        run = started.json()["data"]
        terminal = _wait_for_result(client, run["resultRef"])
        nodes = client.get(run["nodesRef"]).json()["data"]["list"]

    assert terminal["status"] == "SUCCEEDED"
    assert terminal["error"] == ""
    assert terminal["output"]["summary"] == "side_effect_only_completed"
    assert terminal["output"]["sideEffectEvidence"][0]["nodeKey"] == "notify"
    assert "Next node not found" not in str(terminal)
    assert [node["nodeKey"] for node in nodes] == ["notify"]


def _create_workflow(
    client: TestClient,
    *,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Runtime V2 Side Effect Terminal {time.time_ns()}",
            "description": "spec 215.4 terminal side-effect fixture",
            "nodes": nodes,
            "edges": edges,
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
