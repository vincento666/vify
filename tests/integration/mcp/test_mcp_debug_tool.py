import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class McpDebugToolTest(unittest.TestCase):
    def test_debug_tool_returns_result_or_validation_error(self) -> None:
        with TestClient(app) as client:
            server = client.post(
                "/api/v1/mcp-servers",
                json={
                    "name": f"MCP Debug {time.time_ns()}",
                    "endpoint": "mock://tools",
                    "description": "",
                },
            ).json()["data"]

            success_response = client.post(
                f"/api/v1/mcp-servers/{server['id']}/debug",
                json={"toolName": "lookup_order", "arguments": {"orderId": "A-100"}},
            )
            error_response = client.post(
                f"/api/v1/mcp-servers/{server['id']}/debug",
                json={"toolName": "lookup_order", "arguments": {}},
            )

        self.assertEqual(success_response.status_code, 200)
        success = success_response.json()["data"]
        self.assertTrue(success["success"])
        self.assertEqual(success["result"], "Order A-100 status: SHIPPED")
        self.assertIsNone(success["errorMessage"])

        self.assertEqual(error_response.status_code, 200)
        error = error_response.json()["data"]
        self.assertFalse(error["success"])
        self.assertIn("orderId is required", error["errorMessage"])


if __name__ == "__main__":
    unittest.main()
