import unittest

from app.modules.mcp.domain.client import FakeMcpClient


class McpDebugClientTest(unittest.TestCase):
    def test_lookup_order_requires_order_id(self) -> None:
        result = FakeMcpClient().call_tool("mock://tools", "lookup_order", {})

        self.assertFalse(result.success)
        self.assertIn("orderId is required", result.error_message or "")

    def test_lookup_order_returns_mock_result(self) -> None:
        result = FakeMcpClient().call_tool("mock://tools", "lookup_order", {"orderId": "A-100"})

        self.assertTrue(result.success)
        self.assertEqual(result.result, "Order A-100 status: SHIPPED")


if __name__ == "__main__":
    unittest.main()
