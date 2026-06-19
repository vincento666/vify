import time
import unittest
from datetime import datetime
from typing import Any

from fastapi.testclient import TestClient

from app.main import app


class RuntimeV2ToolCallNodeIntegrationTest(unittest.TestCase):
    def test_chatflow_runtime_v2_tool_call_runs_mcp_tool_and_persists_tool_evidence(self) -> None:
        with TestClient(app) as client:
            server_id = _create_mcp_server(client)
            chatflow = _create_tool_call_chatflow(client, server_id)
            started_response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-v2",
                json={"input": {"sys.query": "A-194"}},
            )
            started = started_response.json()["data"]
            terminal = _wait_for_result(client, started["resultRef"])
            nodes = client.get(started["nodesRef"]).json()["data"]["list"]
            events = client.get(started["eventsRef"]).json()["data"]["list"]

        self.assertEqual(started_response.status_code, 200, started_response.text)
        self.assertEqual(terminal["status"], "SUCCEEDED")
        self.assertEqual(terminal["output"], {"final": "客服已查询：Order A-194 status: SHIPPED"})
        tool_node = next(node for node in nodes if node["nodeKey"] == "tool_call_1")
        evidence = tool_node["outputs"]["evidence"]
        self.assertEqual(evidence["resourceType"], "MCP_TOOL")
        self.assertEqual(evidence["toolName"], "lookup_order")
        self.assertEqual(evidence["adapter"], "mcp")
        self.assertEqual(evidence["sanitizedInput"], {"orderId": "A-194"})
        self.assertEqual(evidence["status"], "SUCCEEDED")
        self.assertEqual(evidence["retryCount"], 0)
        self.assertEqual(evidence["attempts"], 1)
        self.assertGreaterEqual(evidence["latencyMs"], 0)
        self.assertGreater(evidence["timeoutMs"], 0)
        completed = next(
            event
            for event in events
            if event["type"] == "workflow_node_completed" and event["nodeId"] == "tool_call_1"
        )
        self.assertEqual(completed["payload"]["output"]["evidence"]["toolName"], "lookup_order")


def _wait_for_result(client: TestClient, result_ref: str, wanted_status: str = "SUCCEEDED", timeout: float = 5.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    latest: dict[str, Any] = {}
    while time.monotonic() < deadline:
        latest = client.get(result_ref).json()["data"]
        if latest["status"] == wanted_status:
            return latest
        if latest["status"] in {"FAILED", "CANCELLED", "INTERRUPTED"} and latest["status"] != wanted_status:
            raise AssertionError(f"Expected {wanted_status}, got {latest}")
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for {wanted_status}; latest={latest}")


def _create_mcp_server(client: TestClient) -> int:
    response = client.post(
        "/api/v1/mcp-servers",
        json={
            "name": f"Runtime V2 Tool Call MCP {datetime.now().timestamp()}",
            "endpoint": "mock://tools",
            "description": "runtime v2 tool call fixture",
            "enabled": True,
        },
    )
    assert response.status_code == 200, response.text
    return int(response.json()["data"]["id"])


def _create_tool_call_chatflow(client: TestClient, server_id: int) -> dict[str, Any]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Runtime V2 Tool Call Chatflow {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "tool_call_1",
                    "type": "TOOL_CALL",
                    "name": "Lookup Order",
                    "config": {
                        "resourceType": "MCP_TOOL",
                        "resourceId": f"mcp:{server_id}:lookup_order",
                        "serverIds": [server_id],
                        "toolName": "lookup_order",
                        "inputMappings": [
                            {"name": "orderId", "valueMode": "reference", "value": "{{start.sys.query}}", "required": True},
                        ],
                        "outputParameters": [
                            {"name": "result", "type": "string"},
                            {"name": "success", "type": "boolean"},
                            {"name": "evidence", "type": "object"},
                        ],
                    },
                },
                {
                    "nodeKey": "message_1",
                    "type": "MESSAGE",
                    "name": "Reply",
                    "config": {"content": "客服已查询：{{tool_call_1.result}}", "outputVariable": "content"},
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{message_1.content}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "tool_call_1", "condition": None},
                {"sourceNodeKey": "tool_call_1", "targetNodeKey": "message_1", "condition": None},
                {"sourceNodeKey": "message_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
