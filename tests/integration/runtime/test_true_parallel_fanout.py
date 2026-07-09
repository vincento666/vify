from __future__ import annotations

import time
import unittest
from datetime import datetime
from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from tests.support.local_api import LocalApiServer

from .nodes._helpers import (
    assert_completed_node_runs,
    assert_wave_started_before_first_completion,
    create_fanout_workflow,
    wait_for_runtime_result,
)


class RuntimeV2TrueParallelFanoutTest(unittest.TestCase):
    def test_three_slow_api_nodes_in_same_frontier_wave_overlap_wall_clock(self) -> None:
        node_keys = {"api_a", "api_b", "api_c"}
        server = LocalApiServer()
        server.start()
        self.addCleanup(server.stop)

        with TestClient(app) as client:
            api_resource = _create_delay_api_resource(client, server.url)
            workflow = create_fanout_workflow(
                client,
                name_prefix="223.2 true parallel API fanout",
                nodes=[
                    _slow_api_node("api_a", api_resource["id"], "a"),
                    _slow_api_node("api_b", api_resource["id"], "b"),
                    _slow_api_node("api_c", api_resource["id"], "c"),
                ],
                output_template="done",
            )
            started_at = time.monotonic()
            started = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"case": "true-parallel"}},
            ).json()["data"]
            terminal = wait_for_runtime_result(client, started["resultRef"], timeout=6)
            elapsed_seconds = time.monotonic() - started_at
            events = client.get(started["eventsRef"]).json()["data"]["list"]
            nodes = client.get(started["nodesRef"]).json()["data"]["list"]

        self.assertEqual(terminal["status"], "SUCCEEDED")
        self.assertEqual(terminal["output"]["final"], "done")
        assert_completed_node_runs(nodes, node_keys, "API_CALL")
        assert_wave_started_before_first_completion(events, node_keys)
        api_nodes = {str(node["nodeKey"]): node for node in nodes if node["nodeKey"] in node_keys}
        wave_keys = {
            str((node.get("selectionState") or {}).get("parallelWaveKey") or "")
            for node in api_nodes.values()
        }
        self.assertEqual(1, len(wave_keys - {""}), api_nodes)
        for node in api_nodes.values():
            self.assertGreater(int(node.get("elapsedMs") or 0), 0, node)
            self.assertTrue(node.get("createdAt"), node)
            self.assertTrue(node.get("finishedAt"), node)
        self.assertLess(
            elapsed_seconds,
            1.7,
            f"Expected three 650ms API branches to overlap; elapsed={elapsed_seconds:.3f}s",
        )


def _create_delay_api_resource(client: TestClient, api_base_url: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/api-resources",
        json={
            "name": f"223.2 Delay API {datetime.now().timestamp()}",
            "description": "Runtime v2 true parallel fanout fixture",
            "method": "GET",
            "endpoint": f"{api_base_url}/delay?branch={{{{branch}}}}&delayMs={{{{delayMs}}}}",
            "authMode": "none",
            "headers": [],
            "bodyTemplate": "",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "branch": {"type": "string"},
                    "delayMs": {"type": "integer"},
                },
                "required": ["branch", "delayMs"],
            },
            "outputSchema": {"type": "object"},
            "timeoutMs": 5000,
            "testPayload": {"branch": "a", "delayMs": 10},
            "enabled": True,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _slow_api_node(node_key: str, api_resource_id: int, branch: str) -> dict[str, object]:
    return {
        "nodeKey": node_key,
        "type": "API_CALL",
        "name": node_key,
        "config": {
            "resourceId": f"api-resource:{api_resource_id}",
            "inputMappings": [
                {"name": "branch", "valueMode": "literal", "value": branch, "required": True},
                {"name": "delayMs", "valueMode": "literal", "value": 650, "required": True},
            ],
            "outputVariable": "payload",
            "timeoutMs": 5000,
        },
    }


if __name__ == "__main__":
    unittest.main()
