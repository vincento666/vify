import unittest

from app.modules.workflow.domain.context import ExecutionContext

try:
    from app.modules.workflow.domain.engine import ConditionBranchPicker, ConditionNodeExecutor
except ImportError:
    ConditionBranchPicker = None  # type: ignore[assignment]
    ConditionNodeExecutor = None  # type: ignore[assignment]


class ConditionBranchingTest(unittest.TestCase):
    def test_condition_executor_renders_expression_into_output_variable(self) -> None:
        self.assertIsNotNone(ConditionNodeExecutor)
        context = ExecutionContext()
        context.set_output("start", {"intent": "vip"})

        output = ConditionNodeExecutor().execute(
            {
                "node_key": "router",
                "type": "CONDITION",
                "config": {"expression": "{{start.intent}}", "outputVariable": "route"},
            },
            context,
        )

        self.assertEqual(output, {"route": "vip"})

    def test_branch_picker_prefers_matching_condition_and_falls_back_to_default(self) -> None:
        self.assertIsNotNone(ConditionBranchPicker)
        edges = [
            {"source_node_key": "router", "target_node_key": "default", "condition_expr": None},
            {"source_node_key": "router", "target_node_key": "vip", "condition_expr": "vip"},
        ]
        picker = ConditionBranchPicker()

        self.assertEqual(picker.pick("router", edges, "vip"), "vip")
        self.assertEqual(picker.pick("router", edges, "unknown"), "default")


if __name__ == "__main__":
    unittest.main()
