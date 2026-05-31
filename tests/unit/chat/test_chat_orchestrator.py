import unittest

from app.modules.chat.domain.llm_request import ChatRequestMessage, FakeOpenAIChatClient
from app.modules.chat.domain.orchestrator import ChatOrchestrator
from app.modules.chat.domain.tool_schema import ToolDefinition
from app.modules.mcp.domain.client import McpCallResult


class _StubMcpFacade:
    def execute_tool_call(
        self,
        server_ids: list[int],
        tool_name: str,
        arguments: dict[str, object],
    ) -> McpCallResult:
        return McpCallResult(True, f"Order {arguments['orderId']} status: SHIPPED", 1)


class ChatOrchestratorTest(unittest.TestCase):
    def test_runs_two_round_tool_flow(self) -> None:
        client = FakeOpenAIChatClient(
            response_payloads=[
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
                    "usage": {"total_tokens": 10},
                },
                {
                    "choices": [
                        {
                            "message": {"content": "Final answer: Order A-100 status: SHIPPED"},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"total_tokens": 20},
                },
            ]
        )
        orchestrator = ChatOrchestrator(llm_client=client)

        result = orchestrator.run(
            model="gpt-4.1-mini",
            messages=[ChatRequestMessage(role="user", content="where is order A-100?")],
            tools=[
                ToolDefinition(
                    name="lookup_order",
                    description="Look up an order",
                    parameters={"type": "object", "properties": {}},
                )
            ],
            tool_ids=[7],
            mcp_facade=_StubMcpFacade(),
        )

        self.assertEqual("Final answer: Order A-100 status: SHIPPED", result.final_content)
        self.assertEqual(2, len(client.captured_payloads))
        self.assertEqual("tool", client.captured_payloads[1]["messages"][-1]["role"])
        self.assertEqual("Order A-100 status: SHIPPED", client.captured_payloads[1]["messages"][-1]["content"])


if __name__ == "__main__":
    unittest.main()
