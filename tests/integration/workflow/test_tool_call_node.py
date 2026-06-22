import unittest
import json
from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app


class WorkflowToolCallNodeIntegrationTest(unittest.TestCase):
    def test_workflow_tool_call_maps_input_outputs_and_persists_evidence(self) -> None:
        with TestClient(app) as client:
            server_id = _create_mcp_server(client)
            workflow = _create_tool_call_workflow(client, server_id)
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-legacy",
                json={"input": {"orderId": "A-100"}},
            )
            debug_response = client.get(
                f"/api/v1/workflows/{workflow['id']}/runs/{response.json()['data']['runId']}/debug"
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(debug_response.status_code, 200, debug_response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"], {"final": "Order A-100 status: SHIPPED"})
        tool_node = next(node for node in debug_response.json()["data"]["nodeDetails"] if node["nodeKey"] == "tool_call_1")
        self.assertEqual(tool_node["resourceType"], "MCP_TOOL")
        self.assertIn("lookup_order", tool_node["resourceId"])
        self.assertGreaterEqual(tool_node["latencyMs"], 0)
        self.assertIn("SHIPPED", tool_node["outputSummary"])

    def test_tool_call_selected_node_rejects_missing_required_mapping(self) -> None:
        with TestClient(app) as client:
            server_id = _create_mcp_server(client)
            workflow = _create_tool_call_workflow(client, server_id)
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/nodes/tool_call_1/runs",
                json={"input": {}},
            )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("orderId is required", response.json()["message"])

    def test_chatflow_tool_call_can_use_sys_query_and_feed_downstream_message(self) -> None:
        with TestClient(app) as client:
            server_id = _create_mcp_server(client)
            chatflow = _create_tool_call_chatflow(client, server_id)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-legacy",
                json={"input": {"sys.query": "A-200"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"], {"final": "客服已查询：Order A-200 status: SHIPPED"})

    def test_tool_call_accepts_json_string_mappings_from_textarea_config(self) -> None:
        with TestClient(app) as client:
            server_id = _create_mcp_server(client)
            workflow = _create_tool_call_workflow(client, server_id, structured_as_text=True)
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-legacy",
                json={"input": {"orderId": "A-500"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"], {"final": "Order A-500 status: SHIPPED"})


def _create_mcp_server(client: TestClient) -> int:
    response = client.post(
        "/api/v1/mcp-servers",
        json={
            "name": f"Tool Call MCP {datetime.now().timestamp()}",
            "endpoint": "mock://tools",
            "description": "tool call fixture",
            "enabled": True,
        },
    )
    assert response.status_code == 200, response.text
    return int(response.json()["data"]["id"])


def _create_tool_call_workflow(client: TestClient, server_id: int, structured_as_text: bool = False) -> dict[str, object]:
    server_ids: list[int] | str = [server_id]
    input_mappings: list[dict[str, object]] | str = [
        {"name": "orderId", "valueMode": "reference", "value": "{{start.orderId}}", "required": True},
    ]
    if structured_as_text:
        server_ids = json.dumps(server_ids)
        input_mappings = json.dumps(input_mappings)
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Tool Call Workflow {datetime.now().timestamp()}",
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
                        "serverIds": server_ids,
                        "toolName": "lookup_order",
                        "inputMappings": input_mappings,
                        "outputParameters": [
                            {"name": "result", "type": "string"},
                            {"name": "success", "type": "boolean"},
                            {"name": "evidence", "type": "object"},
                        ],
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{tool_call_1.result}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "tool_call_1", "condition": None},
                {"sourceNodeKey": "tool_call_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_tool_call_chatflow(client: TestClient, server_id: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Tool Call Chatflow {datetime.now().timestamp()}",
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
                    "config": {
                        "content": "客服已查询：{{tool_call_1.result}}",
                        "outputVariable": "content",
                    },
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
