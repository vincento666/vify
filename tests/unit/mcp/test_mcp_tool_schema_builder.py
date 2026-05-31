import unittest

from app.modules.mcp.domain.client import McpToolDetail

try:
    from app.modules.mcp.domain.schema_builder import McpToolSchemaBuilder
except ModuleNotFoundError:
    McpToolSchemaBuilder = None  # type: ignore[assignment]


class McpToolSchemaBuilderTest(unittest.TestCase):
    def test_builds_chat_tool_schema_from_mcp_tool_details(self) -> None:
        self.assertIsNotNone(McpToolSchemaBuilder)
        tool = McpToolDetail(
            name="lookup_order",
            description="Look up an order",
            input_schema={
                "type": "object",
                "properties": {"orderId": {"type": "string"}},
                "required": ["orderId"],
            },
            required_params=["orderId"],
        )

        schemas = McpToolSchemaBuilder().build([tool])

        self.assertEqual(schemas[0]["name"], "lookup_order")
        self.assertEqual(schemas[0]["parameters"]["required"], ["orderId"])
