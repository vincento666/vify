import unittest

from app.modules.chat.domain.tool_runner import ToolCallRunner
from app.modules.mcp.domain.client import McpCallResult
from app.modules.provider.infra.llm_adapters import ToolCall


class _StubMcpFacade:
    def execute_tool_call(
        self,
        server_ids: list[int],
        tool_name: str,
        arguments: dict[str, object],
    ) -> McpCallResult:
        self.server_ids = server_ids
        self.tool_name = tool_name
        self.arguments = arguments
        return McpCallResult(True, "Order A-100 status: SHIPPED", 3)


class RealToolCallRunnerTest(unittest.TestCase):
    def test_runs_parsed_tool_calls_through_mcp_facade(self) -> None:
        facade = _StubMcpFacade()
        calls = [ToolCall(id="call_1", name="lookup_order", arguments={"orderId": "A-100"})]

        results = ToolCallRunner().run_calls([7], calls, facade)

        self.assertEqual([7], facade.server_ids)
        self.assertEqual("lookup_order", facade.tool_name)
        self.assertEqual({"orderId": "A-100"}, facade.arguments)
        self.assertEqual(1, len(results))
        self.assertTrue(results[0].success)
        self.assertEqual("call_1", results[0].call_id)
        self.assertEqual("Order A-100 status: SHIPPED", results[0].content)


if __name__ == "__main__":
    unittest.main()
