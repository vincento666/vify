import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class McpConnectionAndToolsTest(unittest.TestCase):
    def test_test_connection_and_list_tool_details_for_fake_server(self) -> None:
        with TestClient(app) as client:
            server = _create_server(client, endpoint="mock://tools")

            test_response = client.post(f"/api/v1/mcp-servers/{server['id']}/test")
            tools_response = client.get(f"/api/v1/mcp-servers/{server['id']}/tools")

        self.assertEqual(test_response.status_code, 200)
        test_data = test_response.json()["data"]
        self.assertTrue(test_data["success"])
        self.assertIn("lookup_order", test_data["tools"])
        self.assertIsNone(test_data["errorMessage"])

        self.assertEqual(tools_response.status_code, 200)
        tools = tools_response.json()["data"]
        self.assertEqual(tools[0]["name"], "lookup_order")
        self.assertIn("orderId", tools[0]["inputSchema"]["properties"])
        self.assertEqual(tools[0]["requiredParams"], ["orderId"])

    def test_test_connection_returns_failure_for_unsupported_endpoint(self) -> None:
        with TestClient(app) as client:
            server = _create_server(client, endpoint="http://127.0.0.1:1/mcp")

            response = client.post(f"/api/v1/mcp-servers/{server['id']}/test")

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertFalse(data["success"])
        self.assertEqual(data["tools"], [])
        self.assertIn("Unsupported MCP endpoint", data["errorMessage"])


def _create_server(client: TestClient, endpoint: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/mcp-servers",
        json={
            "name": f"MCP Tools {time.time_ns()}",
            "endpoint": endpoint,
            "description": "",
        },
    )
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
