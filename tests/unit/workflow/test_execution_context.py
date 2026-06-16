import unittest

try:
    from app.modules.workflow.domain.context import ExecutionContext
except ModuleNotFoundError:
    ExecutionContext = None  # type: ignore[assignment]


class ExecutionContextTest(unittest.TestCase):
    def test_resolves_node_variable_templates(self) -> None:
        self.assertIsNotNone(ExecutionContext)
        context = ExecutionContext()
        context.set_output("start", {"userMessage": "reset password"})
        context.set_output("llm", {"answer": "Open settings"})

        rendered = context.render("Question: {{start.userMessage}}; Answer: {{llm.answer}}")

        self.assertEqual(rendered, "Question: reset password; Answer: Open settings")

    def test_converts_scalar_values_to_strings(self) -> None:
        self.assertIsNotNone(ExecutionContext)
        context = ExecutionContext()
        context.set_output("api", {"status": 200, "ok": True})

        self.assertEqual(context.render("status={{api.status}}, ok={{api.ok}}"), "status=200, ok=True")

    def test_missing_variables_render_as_empty_strings(self) -> None:
        self.assertIsNotNone(ExecutionContext)
        context = ExecutionContext()

        self.assertEqual(context.render("{{missing.value}} fallback"), " fallback")

    def test_resolves_flat_variables_that_contain_dots(self) -> None:
        self.assertIsNotNone(ExecutionContext)
        context = ExecutionContext()
        context.set_output("start", {"sys.query": "refund"})

        self.assertEqual(context.render("query={{start.sys.query}}"), "query=refund")

    def test_loads_and_snapshots_variable_scopes(self) -> None:
        self.assertIsNotNone(ExecutionContext)
        context = ExecutionContext()
        context.load_scopes({"conversation": {"topic": "refund"}, "unsupported": {"x": "ignored"}})
        context.set_scope_value("user", "tier", "vip")

        self.assertEqual(context.render("{{conversation.topic}}/{{user.tier}}"), "refund/vip")
        snapshot = context.scopes_snapshot()
        snapshot["conversation"]["topic"] = "mutated"

        self.assertEqual(context.render("{{conversation.topic}}"), "refund")

    def test_local_values_are_scoped_to_current_node_render(self) -> None:
        self.assertIsNotNone(ExecutionContext)
        context = ExecutionContext()

        context.set_local_values({"input": "refund status"})
        self.assertEqual(context.render("User asked {{input}}"), "User asked refund status")

        context.clear_local_values()
        self.assertEqual(context.render("User asked {{input}}"), "User asked {{input}}")


if __name__ == "__main__":
    unittest.main()
