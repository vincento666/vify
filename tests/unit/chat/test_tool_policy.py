import unittest

from app.modules.chat.domain.tool_runner import ToolCallRunner
from app.modules.mcp.domain.client import McpCallResult
from app.modules.provider.infra.llm_adapters import ToolCall


class _RecordingMcpFacade:
    def __init__(self, result: McpCallResult) -> None:
        self.result = result
        self.calls: list[tuple[str, dict[str, object]]] = []

    def execute_tool_call(
        self,
        _server_ids: list[int],
        tool_name: str,
        arguments: dict[str, object],
    ) -> McpCallResult:
        self.calls.append((tool_name, arguments))
        return self.result


class ToolPolicyTest(unittest.TestCase):
    def test_disabled_tool_policy_blocks_execution(self) -> None:
        facade = _RecordingMcpFacade(McpCallResult(True, "ok", 1))
        runner = ToolCallRunner()

        results = runner.run_calls(
            [1],
            [ToolCall(id="call_1", name="lookup_order", arguments={"orderId": "A-100"})],
            facade,
            tool_policies={"lookup_order": {"enabled": False}},
        )

        self.assertEqual([], facade.calls)
        self.assertFalse(results[0].success)
        self.assertEqual("Tool disabled by policy: lookup_order", results[0].error_message)

    def test_tool_policy_presets_arguments_and_timeout(self) -> None:
        facade = _RecordingMcpFacade(McpCallResult(True, "slow result", 50))
        runner = ToolCallRunner()

        results = runner.run_calls(
            [1],
            [ToolCall(id="call_2", name="lookup_order", arguments={"orderId": "A-100"})],
            facade,
            tool_policies={
                "lookup_order": {
                    "argumentPresets": {"orderId": "A-200"},
                    "timeoutMs": 10,
                }
            },
        )

        self.assertEqual([("lookup_order", {"orderId": "A-200"})], facade.calls)
        self.assertFalse(results[0].success)
        self.assertEqual("Tool call timed out: lookup_order", results[0].error_message)


if __name__ == "__main__":
    unittest.main()
