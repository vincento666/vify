import unittest

try:
    from app.modules.chat.domain.tool_runner import ToolCallRunner
except ModuleNotFoundError:
    ToolCallRunner = None  # type: ignore[assignment]


class ToolCallRunnerTest(unittest.TestCase):
    def test_returns_mock_result_only_when_tools_are_bound_and_requested(self) -> None:
        self.assertIsNotNone(ToolCallRunner)
        runner = ToolCallRunner()

        self.assertEqual(runner.run([1], "please use tool"), "Tool mock: please use tool")
        self.assertIsNone(runner.run([], "please use tool"))
        self.assertIsNone(runner.run([1], "normal chat"))

    def test_includes_available_tool_names_when_schema_is_available(self) -> None:
        self.assertIsNotNone(ToolCallRunner)
        runner = ToolCallRunner()

        self.assertEqual(
            runner.run([1], "please use tool", tool_names=["lookup_order"]),
            "Tool mock (lookup_order): please use tool",
        )


if __name__ == "__main__":
    unittest.main()
