import unittest

from app.modules.workflow.domain.context import ExecutionContext

try:
    from app.modules.workflow.domain.engine import EndNodeExecutor, LlmNodeExecutor
except ModuleNotFoundError:
    EndNodeExecutor = None  # type: ignore[assignment]
    LlmNodeExecutor = None  # type: ignore[assignment]


class LinearExecutorTest(unittest.TestCase):
    def test_llm_executor_renders_prompt_into_configured_output_variable(self) -> None:
        self.assertIsNotNone(LlmNodeExecutor)
        context = ExecutionContext()
        context.set_output("start", {"userMessage": "reset password"})

        output = LlmNodeExecutor().execute(
            {
                "node_key": "llm",
                "type": "LLM",
                "config": {"prompt": "User: {{start.userMessage}}", "outputVariable": "answer"},
            },
            context,
        )

        self.assertEqual(output, {"answer": "LLM mock: User: reset password"})

    def test_end_executor_returns_named_output_from_previous_node(self) -> None:
        self.assertIsNotNone(EndNodeExecutor)
        context = ExecutionContext()
        context.set_output("llm", {"answer": "LLM mock: hello"})

        output = EndNodeExecutor().execute(
            {"node_key": "end", "type": "END", "config": {"outputVariable": "answer"}},
            context,
        )

        self.assertEqual(output, {"answer": "LLM mock: hello"})


if __name__ == "__main__":
    unittest.main()
