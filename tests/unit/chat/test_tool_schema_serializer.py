import unittest

from app.modules.chat.domain.tool_schema import OpenAIToolSchemaSerializer, ToolDefinition


class ToolSchemaSerializerTest(unittest.TestCase):
    def test_serializes_tool_definition_to_openai_function_tool(self) -> None:
        tool = ToolDefinition(
            name="lookup_order",
            description="Look up an order",
            parameters={
                "type": "object",
                "properties": {"orderId": {"type": "string"}},
                "required": ["orderId"],
            },
        )

        payload = OpenAIToolSchemaSerializer().serialize([tool])

        self.assertEqual(
            [
                {
                    "type": "function",
                    "function": {
                        "name": "lookup_order",
                        "description": "Look up an order",
                        "parameters": {
                            "type": "object",
                            "properties": {"orderId": {"type": "string"}},
                            "required": ["orderId"],
                        },
                    },
                }
            ],
            payload,
        )


if __name__ == "__main__":
    unittest.main()
