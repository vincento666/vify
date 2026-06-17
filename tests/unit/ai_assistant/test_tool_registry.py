import unittest


class AiAssistantToolRegistryTest(unittest.TestCase):
    def test_echo_context_manifest_is_read_only_and_dispatches(self) -> None:
        from app.modules.ai_assistant.domain.tools import RiskLevel, ToolRegistry

        registry = ToolRegistry.with_builtin_tools()
        manifest = registry.get_manifest("echo_context")

        self.assertEqual(manifest.name, "echo_context")
        self.assertEqual(manifest.risk_level, RiskLevel.READ)
        self.assertEqual(manifest.write_resources, [])
        self.assertIn("message", manifest.input_schema["properties"])

        result = registry.dispatch("echo_context", {"message": "hello harness", "context": {"tenant": "demo"}})

        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(result.output["echo"], "hello harness")
        self.assertEqual(result.output["context"]["tenant"], "demo")

    def test_customer_assistant_bridge_tool_is_read_only_and_returns_refs(self) -> None:
        from app.modules.ai_assistant.domain.tools import RiskLevel, ToolRegistry

        registry = ToolRegistry.with_builtin_tools()
        manifest = registry.get_manifest("customer_assistant_subagent_bridge")

        self.assertEqual(manifest.risk_level, RiskLevel.READ)
        self.assertEqual(manifest.write_resources, [])
        self.assertIn("sessionId", manifest.input_schema["properties"])

        result = registry.dispatch(
            "customer_assistant_subagent_bridge",
            {"sessionId": 12, "runId": 34, "message": "查看客服子任务"},
        )

        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(result.output["agentType"], "customer_assistant")
        self.assertEqual(result.output["subAgentRunId"], "customer-assistant-run-34")
        self.assertIn("/api/v1/customer-assistant/runs/34", result.output["resultRef"])
        self.assertFalse(result.output["cancellation"]["supported"])


if __name__ == "__main__":
    unittest.main()
