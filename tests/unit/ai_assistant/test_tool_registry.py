import unittest
import os
import tempfile
from pathlib import Path


class AiAssistantToolRegistryTest(unittest.TestCase):
    def test_echo_context_manifest_is_read_only_and_dispatches(self) -> None:
        from app.modules.ai_assistant.domain.tools import RiskLevel, ToolRegistry

        registry = ToolRegistry.with_demo_tools()
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
        from app.modules.agent_execution import (
            AgentExecutionCapabilities,
            AgentExecutionStatus,
            SubagentExecutionRef,
        )
        from app.modules.ai_assistant.domain.tools import RiskLevel, ToolRegistry

        registry = ToolRegistry.with_builtin_tools(
            child_execution_adapter=_PersistedSubagentAdapter(
                SubagentExecutionRef(
                    execution_id="customer-assistant-run-34",
                    provider="customer_assistant",
                    child_run_id="34",
                    agent_type="customer_assistant",
                    display_name="客服助手",
                    status=AgentExecutionStatus.RUNNING,
                    current_summary="正在处理客服任务",
                    status_ref="/api/v1/customer-assistant/runs/34",
                    event_stream_ref="/api/v1/customer-assistant/sessions/12/events/stream",
                    result_ref="/api/v1/customer-assistant/runs/34",
                    capabilities=AgentExecutionCapabilities(
                        spawn=False,
                        attach=True,
                        observe=True,
                        cancel=False,
                    ),
                    scope={"tenantId": "tenant-a"},
                    audit={"runId": 34},
                    cancellation={"supported": False},
                )
            ),
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
        self.assertEqual(result.output["status"], "running")
        self.assertEqual(result.output["executionId"], "customer-assistant-run-34")
        self.assertEqual(result.output["subAgentRunId"], "customer-assistant-run-34")
        self.assertIn("/api/v1/customer-assistant/runs/34", result.output["resultRef"])
        self.assertFalse(result.output["cancellation"]["supported"])

    def test_system_knowledge_base_search_tool_is_read_only_and_dispatches(self) -> None:
        from app.modules.ai_assistant.domain.tools import RiskLevel, ToolRegistry

        registry = ToolRegistry.with_demo_tools()
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

    def test_builtin_registry_only_exposes_bound_production_capabilities(self) -> None:
        from app.modules.ai_assistant.domain.tools import ToolRegistry

        manifests = {manifest.name for manifest in ToolRegistry.with_builtin_tools().list_manifests()}

        self.assertIn("run_shell", manifests)
        self.assertIn("read_workspace_file", manifests)
        self.assertIn("invoke_skill", manifests)
        self.assertNotIn("echo_context", manifests)
        self.assertNotIn("update_customer_profile", manifests)
        self.assertNotIn("mock_aviation.refund", manifests)
        self.assertNotIn("search_knowledge_base", manifests)
        self.assertNotIn("run_skill_script", manifests)

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


class _PersistedSubagentAdapter:
    def __init__(self, execution: object) -> None:
        self._execution = execution

    @property
    def provider(self) -> str:
        return "customer_assistant"

    @property
    def display_name(self) -> str:
        return "客服助手"

    @property
    def capabilities(self) -> object:
        return self._execution.capabilities

    def spawn(self, *, parent_execution_id: str, input_payload: dict[str, object]) -> object:
        raise NotImplementedError

    def attach(
        self,
        *,
        parent_execution_id: str,
        session_id: int,
        run_id: int,
    ) -> object:
        return self._execution

    def observe(self, *, execution_id: str) -> object:
        return self._execution

    def cancel(self, *, execution_id: str, actor_id: str) -> object:
        raise NotImplementedError


if __name__ == "__main__":
    unittest.main()
