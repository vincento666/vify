import unittest

from app.modules.chat.domain.tool_runner import (
    ToolCallRunner,
    clear_tool_audit_log,
    list_tool_audit_log,
)
from app.modules.mcp.domain.client import McpCallResult
from app.modules.provider.infra.llm_adapters import ToolCall


class _SequencedMcpFacade:
    def __init__(self, results: list[McpCallResult]) -> None:
        self._results = list(results)

    def execute_tool_call(
        self,
        server_ids: list[int],
        tool_name: str,
        arguments: dict[str, object],
    ) -> McpCallResult:
        return self._results.pop(0)


class ToolExecutionHardeningTest(unittest.TestCase):
    def setUp(self) -> None:
        clear_tool_audit_log()

    def test_runner_marks_slow_tool_result_as_timeout_and_audits_it(self) -> None:
        calls = [ToolCall(id="call_slow", name="lookup_order", arguments={"orderId": "A-100"})]
        facade = _SequencedMcpFacade([McpCallResult(True, "slow result", 50)])

        results = ToolCallRunner(max_elapsed_ms=10).run_calls([1], calls, facade)

        self.assertFalse(results[0].success)
        self.assertEqual("Tool call timed out: lookup_order", results[0].error_message)
        audit = list_tool_audit_log()
        self.assertEqual(1, len(audit))
        self.assertEqual("lookup_order", audit[0].tool_name)
        self.assertFalse(audit[0].success)
        self.assertEqual("Tool call timed out: lookup_order", audit[0].error_message)

    def test_runner_keeps_partial_failure_results(self) -> None:
        calls = [
            ToolCall(id="call_ok", name="lookup_order", arguments={"orderId": "A-100"}),
            ToolCall(id="call_fail", name="refund_order", arguments={}),
        ]
        facade = _SequencedMcpFacade(
            [
                McpCallResult(True, "Order A-100 status: SHIPPED", 1),
                McpCallResult(False, None, 1, "orderId is required"),
            ]
        )

        results = ToolCallRunner().run_calls([1], calls, facade)

        self.assertEqual([True, False], [result.success for result in results])
        self.assertEqual("Order A-100 status: SHIPPED", results[0].content)
        self.assertEqual("orderId is required", results[1].error_message)
        self.assertEqual(2, len(list_tool_audit_log()))


if __name__ == "__main__":
    unittest.main()
