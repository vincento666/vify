import unittest
import os
import tempfile
from pathlib import Path


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
        from app.modules.customer_assistant.harness_adapter import CustomerAssistantExecutionAdapter

        registry = ToolRegistry.with_builtin_tools(
            child_execution_adapter=CustomerAssistantExecutionAdapter(),
        )
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

    def test_system_knowledge_base_search_tool_is_read_only_and_dispatches(self) -> None:
        from app.modules.ai_assistant.domain.tools import RiskLevel, ToolRegistry

        registry = ToolRegistry.with_builtin_tools()
        manifest = registry.get_manifest("search_knowledge_base")

        self.assertEqual(manifest.risk_level, RiskLevel.READ)
        self.assertEqual(manifest.write_resources, [])
        self.assertIn("query", manifest.input_schema["properties"])
        self.assertIn("knowledgeBaseId", manifest.input_schema["properties"])
        self.assertIn("knowledge_base", manifest.read_resources)

        result = registry.dispatch(
            "search_knowledge_base",
            {"query": "退票规则", "knowledgeBaseId": 12, "limit": 3},
        )

        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(result.output["query"], "退票规则")
        self.assertEqual(result.output["knowledgeBaseId"], 12)
        self.assertEqual(result.output["limit"], 3)
        self.assertEqual(result.output["source"], "system_knowledge_base")
        self.assertIn("hits", result.output)

    def test_run_shell_executes_controlled_workspace_command(self) -> None:
        from app.modules.ai_assistant.domain.tools import ToolRegistry

        with tempfile.TemporaryDirectory() as workspace:
            previous = os.environ.get("HIFY_WORKSPACE_ROOT")
            os.environ["HIFY_WORKSPACE_ROOT"] = workspace
            try:
                script = Path(workspace) / "tmp" / "controlled-shell.mjs"
                script.parent.mkdir(parents=True)
                script.write_text("console.log('PASS controlled shell')\n", encoding="utf-8")

                result = ToolRegistry.with_builtin_tools().dispatch(
                    "run_shell",
                    {"command": "node tmp/controlled-shell.mjs"},
                )
            finally:
                if previous is None:
                    os.environ.pop("HIFY_WORKSPACE_ROOT", None)
                else:
                    os.environ["HIFY_WORKSPACE_ROOT"] = previous

        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(result.output["exitCode"], 0)
        self.assertIn("PASS controlled shell", result.output["stdout"])
        self.assertEqual(result.output["stderr"], "")


if __name__ == "__main__":
    unittest.main()
