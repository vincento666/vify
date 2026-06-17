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


if __name__ == "__main__":
    unittest.main()
