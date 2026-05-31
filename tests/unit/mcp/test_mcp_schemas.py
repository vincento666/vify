import unittest

try:
    from app.modules.mcp.web.schemas import McpServerCreateRequest, McpServerUpdateRequest
except ImportError:
    McpServerCreateRequest = None  # type: ignore[assignment]
    McpServerUpdateRequest = None  # type: ignore[assignment]


class McpSchemaTest(unittest.TestCase):
    def test_create_request_accepts_required_fields(self) -> None:
        self.assertIsNotNone(McpServerCreateRequest)

        request = McpServerCreateRequest(
            name="Order MCP",
            endpoint="mock://tools",
            description="orders",
        )

        self.assertEqual(request.name, "Order MCP")
        self.assertEqual(request.endpoint, "mock://tools")

    def test_update_request_accepts_enabled_flag(self) -> None:
        self.assertIsNotNone(McpServerUpdateRequest)

        request = McpServerUpdateRequest(
            name="Order MCP",
            endpoint="mock://tools",
            enabled=0,
        )

        self.assertEqual(request.enabled, 0)


if __name__ == "__main__":
    unittest.main()
