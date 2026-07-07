from __future__ import annotations

import time
import unittest
from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app


class RuntimeV2ConcurrentFanoutTest(unittest.TestCase):
    def test_explicit_default_fanout_runs_all_frontier_nodes_before_join(self) -> None:
        with TestClient(app) as client:
            workflow = _create_fanout_workflow(client)
            started = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"sys.query": "refund"}},
            )
            self.assertEqual(started.status_code, 200, started.text)
            run = started.json()["data"]
            terminal = _wait_for_result(client, run["resultRef"])
            events = client.get(run["eventsRef"]).json()["data"]["list"]
            nodes = client.get(run["nodesRef"]).json()["data"]["list"]

        self.assertEqual(terminal["status"], "SUCCEEDED")
        self.assertEqual(terminal["output"], {"final": "A refund|B refund"})
        self.assertEqual([node["nodeKey"] for node in nodes], ["message_a", "message_b", "end"])
        self.assertEqual([node["status"] for node in nodes], ["COMPLETED", "COMPLETED", "COMPLETED"])
        completed_before_end = [
            event["nodeId"]
            for event in events
            if event["type"] == "workflow_node_completed" and event["nodeId"] in {"message_a", "message_b"}
        ]
        self.assertEqual(completed_before_end, ["message_a", "message_b"])


def _create_fanout_workflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Runtime V2 Fanout {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {
                    "nodeKey": "start",
                    "type": "START",
                    "name": "Start",
                    "config": {"ports": [{"key": "default", "allowFanOut": True}]},
                },
                {
                    "nodeKey": "message_a",
                    "type": "MESSAGE",
                    "name": "A",
                    "config": {"content": "A {{start.sys.query}}", "outputVariable": "a"},
                },
                {
                    "nodeKey": "message_b",
                    "type": "MESSAGE",
                    "name": "B",
                    "config": {"content": "B {{start.sys.query}}", "outputVariable": "b"},
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{message_a.a}}|{{message_b.b}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "message_a", "condition": None},
                {"sourceNodeKey": "start", "targetNodeKey": "message_b", "condition": None},
                {"sourceNodeKey": "message_a", "targetNodeKey": "end", "condition": None},
                {"sourceNodeKey": "message_b", "targetNodeKey": "end", "condition": None},
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
