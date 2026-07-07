import time
import unittest
from typing import Any

from fastapi.testclient import TestClient

from app.main import app


class WorkflowNoFinalOutputContractTest(unittest.TestCase):
    def test_side_effect_only_workflow_returns_status_events_and_side_effect_evidence(self) -> None:
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
                                '"sideEffectEvidence": {"channel": "ops", "idempotencyKey": "workflow-2144"}'
                                "}"
                            ),
                        },
                    ),
                    _node("end", "END"),
                ],
                edges=[_edge("start", "notify")],
            )
            published = client.post(f"/api/v1/workflows/{workflow['id']}/publish")
            self.assertEqual(published.status_code, 200, published.text)
            started = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"sys.query": "workflow side effect only"}},
            ).json()["data"]
            terminal = _wait_for_result(client, started["resultRef"])
            events = client.get(started["eventsRef"]).json()["data"]["list"]
            nodes = client.get(started["nodesRef"]).json()["data"]["list"]

        self.assertEqual(terminal["status"], "SUCCEEDED")
        self.assertEqual(terminal["ownerType"], "WORKFLOW")
        self.assertTrue(terminal["output"]["sideEffectOnly"])
        self.assertEqual(terminal["output"]["summary"], "side_effect_only_completed")
        self.assertEqual(terminal["output"]["sideEffectEvidence"][0]["nodeKey"], "notify")
        self.assertTrue(any(event["type"] == "workflow_node_completed" for event in events), events)
        self.assertEqual([node["nodeKey"] for node in nodes], ["notify"])


def _create_workflow(
    client: TestClient,
    *,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Workflow Side Effect Only {time.time_ns()}",
            "description": "spec 214.4 no-final-output fixture",
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
