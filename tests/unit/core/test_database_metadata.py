import unittest

from app.core.database import Base
from app.core.schema import register_baseline_tables


EXPECTED_TABLES = {
    "provider",
    "model_config",
    "provider_health",
    "mcp_server",
    "agent",
    "agent_tool",
    "chat_session",
    "chat_message",
    "knowledge_base",
    "document",
    "workflow",
    "workflow_node",
    "workflow_edge",
    "workflow_run",
    "workflow_node_run",
    "eval_set",
    "eval_case",
    "evaluator",
    "evaluation_experiment",
    "evaluation_run",
    "evaluation_case_result",
}


class DatabaseMetadataTest(unittest.TestCase):
    def test_baseline_metadata_contains_source_superset(self) -> None:
        register_baseline_tables()

        self.assertTrue(EXPECTED_TABLES.issubset(set(Base.metadata.tables)))

    def test_agent_contains_augmented_links(self) -> None:
        register_baseline_tables()

        agent_columns = set(Base.metadata.tables["agent"].columns.keys())

        self.assertIn("knowledge_base_id", agent_columns)
        self.assertIn("workflow_id", agent_columns)

    def test_workflow_contains_flow_type(self) -> None:
        register_baseline_tables()

        workflow_columns = set(Base.metadata.tables["workflow"].columns.keys())

        self.assertIn("flow_type", workflow_columns)


if __name__ == "__main__":
    unittest.main()
