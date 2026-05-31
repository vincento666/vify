import unittest

from app.modules.provider.infra.llm_adapters import OpenAIAdapterParser


class ToolCallParserTest(unittest.TestCase):
    def test_openai_tool_calls_are_parsed_to_internal_calls(self) -> None:
        result = OpenAIAdapterParser().parse_chat_response(
            {
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {
                                        "name": "lookup_order",
                                        "arguments": '{"orderId":"A-100"}',
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {"total_tokens": 24},
            }
        )

        self.assertEqual("", result.content)
        self.assertEqual("tool_calls", result.finish_reason)
        self.assertEqual(24, result.tokens)
        self.assertEqual(1, len(result.tool_calls))
        self.assertEqual("call_1", result.tool_calls[0].id)
        self.assertEqual("lookup_order", result.tool_calls[0].name)
        self.assertEqual({"orderId": "A-100"}, result.tool_calls[0].arguments)


if __name__ == "__main__":
    unittest.main()
