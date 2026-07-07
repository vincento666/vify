from __future__ import annotations

import time
import unittest
from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.modules.runtime.domain.scheduler import compute_frontier


class FrontierSchedulerSequentialParityTest(unittest.TestCase):
    def test_runtime_v2_uses_frontier_scheduler_without_changing_linear_order(self) -> None:
        with patch("app.modules.workflow.domain.runtime_v2.compute_frontier", wraps=compute_frontier) as frontier:
            with TestClient(app) as client:
                workflow = _create_linear_message_workflow(client)
                started = client.post(
                    f"/api/v1/workflows/{workflow['id']}/runs",
                    json={"input": {"sys.query": "hello frontier"}},
                ).json()["data"]
                terminal = _wait_for_result(client, started["resultRef"])
                events = client.get(started["eventsRef"]).json()["data"]["list"]
                nodes = client.get(started["nodesRef"]).json()["data"]["list"]

        self.assertGreaterEqual(frontier.call_count, 2)
        self.assertEqual(terminal["status"], "SUCCEEDED")
        self.assertEqual(terminal["output"], {"final": "frontier ok"})
        self.assertEqual([node["nodeKey"] for node in nodes], ["message_1", "end"])
        self.assertEqual([node["status"] for node in nodes], ["COMPLETED", "COMPLETED"])
        self.assertEqual(
            [event["nodeId"] for event in events if event["type"] == "workflow_node_started"],
            ["message_1", "end"],
        )
        self.assertEqual(
            [event["nodeId"] for event in events if event["type"] == "workflow_node_completed"],
            ["message_1", "end"],
        )


def _create_linear_message_workflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Frontier sequential parity {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "message_1",
                    "type": "MESSAGE",
                    "name": "Message",
                    "config": {"content": "frontier ok", "outputVariable": "content"},
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


def _wait_for_result(client: TestClient, result_ref: str, timeout: float = 5.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        latest = client.get(result_ref).json()["data"]
        if latest["status"] in {"SUCCEEDED", "FAILED", "INTERRUPTED"}:
            return latest
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for terminal result; latest={latest}")


if __name__ == "__main__":
    unittest.main()
