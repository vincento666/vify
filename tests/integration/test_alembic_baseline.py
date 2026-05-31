import tempfile
import unittest
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


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
}


class AlembicBaselineTest(unittest.TestCase):
    def test_upgrade_head_creates_baseline_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "hify.db"
            database_url = f"sqlite:///{db_path}"
            config = Config("alembic.ini")
            config.set_main_option("script_location", "alembic")
            config.set_main_option("sqlalchemy.url", database_url)

            command.upgrade(config, "head")

            engine = create_engine(database_url)
            inspector = inspect(engine)
            table_names = set(inspector.get_table_names())
            agent_columns = {column["name"] for column in inspector.get_columns("agent")}

            self.assertTrue(EXPECTED_TABLES.issubset(table_names))
            self.assertIn("knowledge_base_id", agent_columns)
            self.assertIn("workflow_id", agent_columns)


if __name__ == "__main__":
    unittest.main()
