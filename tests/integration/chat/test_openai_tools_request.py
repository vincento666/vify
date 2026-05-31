import unittest

from app.modules.chat.domain.llm_request import (
    ChatRequestMessage,
    FakeOpenAIChatClient,
    OpenAIChatRequestBuilder,
)
from app.modules.chat.domain.tool_schema import ToolDefinition


class OpenAIToolsRequestTest(unittest.TestCase):
    def test_fake_llm_captures_openai_tools_payload(self) -> None:
        tool = ToolDefinition(
            name="lookup_order",
            description="Look up an order",
            parameters={
                "type": "object",
                "properties": {"orderId": {"type": "string"}},
                "required": ["orderId"],
            },
        )
        payload = OpenAIChatRequestBuilder().build(
            model="gpt-4.1-mini",
            messages=[ChatRequestMessage(role="user", content="check order A-100")],
            tools=[tool],
        )
        client = FakeOpenAIChatClient()

        client.complete(payload)

        self.assertEqual("gpt-4.1-mini", client.captured_payload["model"])
        self.assertEqual("check order A-100", client.captured_payload["messages"][0]["content"])
        self.assertEqual("function", client.captured_payload["tools"][0]["type"])
        self.assertEqual("lookup_order", client.captured_payload["tools"][0]["function"]["name"])


if __name__ == "__main__":
    unittest.main()
