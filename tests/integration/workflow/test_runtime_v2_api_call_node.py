import time
import unittest
from datetime import datetime
from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from tests.support.local_api import LocalApiServer


class RuntimeV2ApiCallNodeIntegrationTest(unittest.TestCase):
    def test_chatflow_runtime_v2_api_call_uses_api_resource_and_persists_sanitized_evidence(self) -> None:
        server = LocalApiServer()
        server.start()
        self.addCleanup(server.stop)

        with TestClient(app) as client:
            api_resource = _create_api_resource(client, server.url)
            chatflow = _create_api_call_chatflow(client, int(api_resource["id"]))
            started_response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-v2",
                json={"input": {"orderId": "A-194"}},
            )
            started = started_response.json()["data"]
            terminal = _wait_for_result(client, started["resultRef"])
            nodes = client.get(started["nodesRef"]).json()["data"]["list"]
            events = client.get(started["eventsRef"]).json()["data"]["list"]

        self.assertEqual(started_response.status_code, 200, started_response.text)
        self.assertEqual(terminal["status"], "SUCCEEDED")
        self.assertEqual(terminal["output"], {"final": "API_REAL: GET /text/orders/A-194"})
        api_node = next(node for node in nodes if node["nodeKey"] == "api_call_1")
        evidence = api_node["outputs"]["evidence"]
        self.assertEqual(evidence["resourceId"], f"api-resource:{api_resource['id']}")
        self.assertEqual(evidence["resourceType"], "API_RESOURCE")
        self.assertEqual(evidence["adapter"], "API_RESOURCE")
        self.assertEqual(evidence["sanitizedInput"], {"orderId": "A-194"})
        self.assertEqual(evidence["sanitizedRequest"]["headers"]["X-Test-Token"], "***")
        self.assertEqual(evidence["response"]["bodyPreview"], "API_REAL: GET /text/orders/A-194")
        self.assertGreaterEqual(evidence["latencyMs"], 0)
        self.assertEqual(evidence["status"], "SUCCEEDED")
        self.assertNotIn("secret-token", str(api_node["outputs"]))
        completed = next(
            event
            for event in events
            if event["type"] == "workflow_node_completed" and event["nodeId"] == "api_call_1"
        )
        self.assertEqual(completed["payload"]["output"]["evidence"]["status"], "SUCCEEDED")

    def test_runtime_v2_rejects_direct_url_api_call_at_compatibility_boundary(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_direct_url_api_call_chatflow(client)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-v2",
                json={"input": {"orderId": "A-unsafe"}},
            )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("api_call_requires_api_resource", response.json()["message"])


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


def _create_api_resource(client: TestClient, api_base_url: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/api-resources",
        json={
            "name": f"Runtime V2 Orders API {datetime.now().timestamp()}",
            "description": "Runtime v2 API_CALL fixture",
            "method": "GET",
            "endpoint": f"{api_base_url}/text/orders/{{{{orderId}}}}",
            "authMode": "none",
            "headers": [{"name": "X-Test-Token", "value": "secret-token", "sensitive": True}],
            "bodyTemplate": "",
            "inputSchema": {
                "type": "object",
                "properties": {"orderId": {"type": "string"}},
                "required": ["orderId"],
            },
            "outputSchema": {"type": "object", "properties": {"body": {"type": "string"}}},
            "timeoutMs": 5000,
            "testPayload": {"orderId": "A-194"},
            "enabled": True,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_api_call_chatflow(client: TestClient, api_resource_id: int) -> dict[str, Any]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Runtime V2 API Call Chatflow {datetime.now().timestamp()}",
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


def _create_direct_url_api_call_chatflow(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Runtime V2 Unsafe API Call Chatflow {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "api_call_1",
                    "type": "API_CALL",
                    "name": "Unsafe Direct URL",
                    "config": {"method": "GET", "url": "https://example.test/orders/{{start.orderId}}"},
                },
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final"}},
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
