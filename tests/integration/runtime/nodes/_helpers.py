from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from fastapi.testclient import TestClient


def wait_for_runtime_result(
    client: TestClient,
    result_ref: str,
    wanted_status: str = "SUCCEEDED",
    timeout: float = 5.0,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    latest: dict[str, Any] = {}
    terminal_statuses = {"SUCCEEDED", "FAILED", "INTERRUPTED", "CANCELLED"}
    while time.monotonic() < deadline:
        latest = client.get(result_ref).json()["data"]
        if latest["status"] == wanted_status:
            return latest
        if latest["status"] in terminal_statuses and latest["status"] != wanted_status:
            raise AssertionError(f"Expected {wanted_status}, got {latest}")
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for {wanted_status}; latest={latest}")


def create_fanout_workflow(
    client: TestClient,
    *,
    name_prefix: str,
    nodes: list[dict[str, Any]],
    output_template: str,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"{name_prefix} {datetime.now().timestamp()}",
            "description": "runtime v2 node concurrency fixture",
            "nodes": [
                {
                    "nodeKey": "start",
                    "type": "START",
                    "name": "Start",
                    "config": {"ports": [{"key": "default", "allowFanOut": True}]},
                },
                *nodes,
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": output_template},
                },
            ],
            "edges": [
                *[
                    {"sourceNodeKey": "start", "targetNodeKey": str(node["nodeKey"]), "condition": None}
                    for node in nodes
                ],
                *[
                    {"sourceNodeKey": str(node["nodeKey"]), "targetNodeKey": "end", "condition": None}
                    for node in nodes
                ],
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def assert_wave_started_before_first_completion(events: list[dict[str, Any]], node_keys: set[str]) -> None:
    first_completed_index = next(
        index
        for index, event in enumerate(events)
        if event.get("type") == "workflow_node_completed" and event.get("nodeId") in node_keys
    )
    started_before_completion = {
        str(event.get("nodeId"))
        for event in events[:first_completed_index]
        if event.get("type") == "workflow_node_started" and event.get("nodeId") in node_keys
    }
    assert started_before_completion == node_keys, events


def assert_completed_node_runs(nodes: list[dict[str, Any]], node_keys: set[str], node_type: str) -> None:
    rows = {str(node["nodeKey"]): node for node in nodes if node["nodeKey"] in node_keys}
    assert set(rows) == node_keys
    for node_key, row in rows.items():
        assert row["nodeType"] == node_type, node_key
        assert row["status"] == "COMPLETED", node_key
        assert row["observability"]["nodeState"] == "COMPLETED", node_key
        assert row["eventsRef"].endswith(f"/runtime-runs/{row['runId']}/events"), node_key
