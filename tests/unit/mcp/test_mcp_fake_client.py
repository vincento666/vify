import unittest

try:
    from app.modules.mcp.domain.client import FakeMcpClient
except ModuleNotFoundError:
    FakeMcpClient = None  # type: ignore[assignment]


class McpFakeClientTest(unittest.TestCase):
    def test_mock_tools_endpoint_returns_success_and_tool_names(self) -> None:
        self.assertIsNotNone(FakeMcpClient)

        result = FakeMcpClient().test_connection("mock://tools")

        self.assertTrue(result.success)
        self.assertIn("lookup_order", result.tools)
        self.assertIsNone(result.error_message)

    def test_unknown_endpoint_returns_structured_failure(self) -> None:
        self.assertIsNotNone(FakeMcpClient)

        result = FakeMcpClient().test_connection("http://127.0.0.1:1/mcp")

        self.assertFalse(result.success)
        self.assertEqual(result.tools, [])
        self.assertIn("Unsupported MCP endpoint", result.error_message or "")


if __name__ == "__main__":
    unittest.main()
