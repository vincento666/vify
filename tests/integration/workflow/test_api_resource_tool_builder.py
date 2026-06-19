import unittest
from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app
from tests.support.local_api import LocalApiServer


class ApiResourceToolBuilderIntegrationTest(unittest.TestCase):
    def test_api_resource_can_be_tested_wrapped_as_tool_and_called_by_workflow(self) -> None:
        server = LocalApiServer()
        server.start()
        self.addCleanup(server.stop)

        with TestClient(app) as client:
            api_resource = _create_api_resource(client, server.url)
            listed_resources = client.get("/api/v1/api-resources")
            test_call = client.post(
                f"/api/v1/api-resources/{api_resource['id']}/test-call",
                json={"input": {"orderId": "A-100"}},
            )
            api_tool = _create_api_tool(client, int(api_resource["id"]))
            registry_response = client.get(
                "/api/v1/workflow-resources",
                params={"flowType": "WORKFLOW", "resourceType": "API_TOOL"},
            )
            workflow = _create_api_tool_workflow(client, str(api_tool["resourceId"]))
            run_response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-legacy",
                json={"input": {"orderId": "A-100"}},
            )
            debug_response = client.get(
                f"/api/v1/workflows/{workflow['id']}/runs/{run_response.json()['data']['runId']}/debug"
            )

        self.assertEqual(listed_resources.status_code, 200, listed_resources.text)
        listed_data = listed_resources.json()["data"]
        self.assertIn(api_resource["id"], [item["id"] for item in listed_data["list"]])
        self.assertEqual(test_call.status_code, 200, test_call.text)
        self.assertEqual(test_call.json()["data"]["status"], "SUCCEEDED")
        self.assertEqual(test_call.json()["data"]["response"]["body"], "API_REAL: GET /text/orders/A-100")
        self.assertEqual(test_call.json()["data"]["evidence"]["adapter"], "API_RESOURCE")
        self.assertNotIn("secret", str(test_call.json()["data"]["evidence"]).lower())

        self.assertEqual(registry_response.status_code, 200, registry_response.text)
        registry_items = registry_response.json()["data"]["list"]
        self.assertTrue(
            any(item["resourceId"] == api_tool["resourceId"] and item["resourceType"] == "API_TOOL" for item in registry_items),
            registry_response.text,
        )

        self.assertEqual(run_response.status_code, 200, run_response.text)
        run_data = run_response.json()["data"]
        self.assertEqual(run_data["status"], "SUCCEEDED")
        self.assertEqual(run_data["output"], {"final": "API_REAL: GET /text/orders/A-100"})

        self.assertEqual(debug_response.status_code, 200, debug_response.text)
        tool_node = next(node for node in debug_response.json()["data"]["nodeDetails"] if node["nodeKey"] == "tool_call_1")
        self.assertEqual(tool_node["resourceType"], "API_TOOL")
        self.assertIn("lookup_order_api", tool_node["resourceId"])
        self.assertIn("API_REAL", tool_node["outputSummary"])
        self.assertGreaterEqual(tool_node["latencyMs"], 0)

    def test_direct_api_call_can_reference_api_resource_with_mapped_inputs(self) -> None:
        server = LocalApiServer()
        server.start()
        self.addCleanup(server.stop)

        with TestClient(app) as client:
            api_resource = _create_api_resource(client, server.url)
            workflow = _create_api_resource_call_workflow(client, int(api_resource["id"]))
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-legacy",
                json={"input": {"orderId": "A-220"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"], {"final": "API_REAL: GET /text/orders/A-220"})


def _create_api_resource(client: TestClient, api_base_url: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/api-resources",
        json={
            "name": f"Orders API {datetime.now().timestamp()}",
            "description": "Lookup order fixture",
            "method": "GET",
            "endpoint": f"{api_base_url}/text/orders/{{{{orderId}}}}",
            "authMode": "none",
            "headers": [
                {"name": "X-Test-Token", "value": "secret-token", "sensitive": True},
            ],
            "bodyTemplate": "",
            "inputSchema": {
                "type": "object",
                "properties": {"orderId": {"type": "string"}},
                "required": ["orderId"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {"body": {"type": "string"}},
            },
            "timeoutMs": 5000,
            "testPayload": {"orderId": "A-100"},
            "enabled": True,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_api_tool(client: TestClient, api_resource_id: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/tools",
        json={
            "name": f"lookup_order_api_{datetime.now().timestamp()}",
            "displayName": "查询订单 API",
            "description": "Lookup order through an API Resource",
            "adapterType": "API_RESOURCE",
            "apiResourceId": api_resource_id,
            "inputSchema": {
                "type": "object",
                "properties": {"orderId": {"type": "string"}},
                "required": ["orderId"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
            },
            "modelCallable": True,
            "enabled": True,
            "timeoutMs": 5000,
            "retryCount": 0,
            "errorBehavior": "fail",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_api_tool_workflow(client: TestClient, resource_id: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"API Tool Workflow {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "tool_call_1",
                    "type": "TOOL_CALL",
                    "name": "Lookup Order API",
                    "config": {
                        "resourceType": "API_TOOL",
                        "resourceId": resource_id,
                        "toolName": "lookup_order_api",
                        "inputMappings": [
                            {"name": "orderId", "valueMode": "reference", "value": "{{start.orderId}}", "required": True},
                        ],
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


def _create_api_resource_call_workflow(client: TestClient, api_resource_id: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"API Resource Call Workflow {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "api_call_1",
                    "type": "API_CALL",
                    "name": "Orders API",
                    "config": {
                        "resourceId": f"api-resource:{api_resource_id}",
                        "inputMappings": [
                            {"name": "orderId", "valueMode": "reference", "value": "{{start.orderId}}", "required": True},
                        ],
                        "outputVariable": "answer",
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{api_call_1.answer}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "api_call_1", "condition": None},
                {"sourceNodeKey": "api_call_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
