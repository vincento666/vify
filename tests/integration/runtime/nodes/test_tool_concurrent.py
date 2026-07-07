from __future__ import annotations

import unittest
from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app

from ._helpers import (
    assert_completed_node_runs,
    assert_wave_started_before_first_completion,
    create_fanout_workflow,
    wait_for_runtime_result,
)


class RuntimeV2ToolConcurrentTest(unittest.TestCase):
    def test_three_tool_call_nodes_in_same_frontier_wave_keep_outputs_and_events_isolated(self) -> None:
        node_keys = {"tool_a", "tool_b", "tool_c"}
        with TestClient(app) as client:
            server_id = _create_mcp_server(client)
            workflow = create_fanout_workflow(
                client,
                name_prefix="217.3 Tool fanout",
                nodes=[
                    _tool_node("tool_a", server_id, "orderA"),
                    _tool_node("tool_b", server_id, "orderB"),
                    _tool_node("tool_c", server_id, "orderC"),
                ],
                output_template="{{tool_a.result}}|{{tool_b.result}}|{{tool_c.result}}",
            )
            started = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"orderA": "A-2173", "orderB": "B-2173", "orderC": "C-2173"}},
            ).json()["data"]
            terminal = wait_for_runtime_result(client, started["resultRef"])
            events = client.get(started["eventsRef"]).json()["data"]["list"]
            nodes = client.get(started["nodesRef"]).json()["data"]["list"]

        self.assertEqual(
            terminal["output"]["final"],
            "Order A-2173 status: SHIPPED|Order B-2173 status: SHIPPED|Order C-2173 status: SHIPPED",
        )
        assert_completed_node_runs(nodes, node_keys, "TOOL_CALL")
        assert_wave_started_before_first_completion(events, node_keys)


def _create_mcp_server(client: TestClient) -> int:
    response = client.post(
        "/api/v1/mcp-servers",
        json={
            "name": f"217.3 Tool MCP {datetime.now().timestamp()}",
            "endpoint": "mock://tools",
            "description": "runtime v2 tool concurrency fixture",
            "enabled": True,
        },
    )
    assert response.status_code == 200, response.text
    return int(response.json()["data"]["id"])


def _tool_node(node_key: str, server_id: int, input_key: str) -> dict[str, object]:
    return {
        "nodeKey": node_key,
        "type": "TOOL_CALL",
        "name": node_key,
        "config": {
            "resourceType": "MCP_TOOL",
            "resourceId": f"mcp:{server_id}:lookup_order",
            "serverIds": [server_id],
            "toolName": "lookup_order",
            "inputMappings": [
                {"name": "orderId", "valueMode": "reference", "value": f"{{{{start.{input_key}}}}}", "required": True},
            ],
            "outputParameters": [
                {"name": "result", "type": "string"},
                {"name": "success", "type": "boolean"},
                {"name": "evidence", "type": "object"},
            ],
        },
    }


if __name__ == "__main__":
    unittest.main()
