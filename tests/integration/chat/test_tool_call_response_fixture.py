import unittest

from app.modules.chat.domain.llm_request import (
    ChatRequestMessage,
    FakeOpenAIChatClient,
    OpenAIChatRequestBuilder,
)
from app.modules.chat.domain.tool_schema import ToolDefinition
from app.modules.provider.infra.llm_adapters import OpenAIAdapterParser


class ToolCallResponseFixtureTest(unittest.TestCase):
    def test_fake_llm_tool_call_response_is_parsed(self) -> None:
        client = FakeOpenAIChatClient(
            response_payload={
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_lookup",
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
                "usage": {"total_tokens": 32},
            }
        )
        payload = OpenAIChatRequestBuilder().build(
            model="gpt-4.1-mini",
            messages=[ChatRequestMessage(role="user", content="where is A-100?")],
            tools=[
                ToolDefinition(
                    name="lookup_order",
                    description="Look up an order",
                    parameters={"type": "object", "properties": {}},
                )
            ],
        )

        parsed = OpenAIAdapterParser().parse_chat_response(client.complete(payload))

        self.assertEqual("lookup_order", parsed.tool_calls[0].name)
        self.assertEqual({"orderId": "A-100"}, parsed.tool_calls[0].arguments)


if __name__ == "__main__":
    unittest.main()
