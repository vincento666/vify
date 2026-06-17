import unittest

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from tests.support.mysql import configured_mysql8_database_url, mysql8_database_url


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
        with mysql8_database_url("alembic_baseline") as database_url:
            config = Config("alembic.ini")
            config.set_main_option("script_location", "alembic")
            config.set_main_option("sqlalchemy.url", database_url)

            with configured_mysql8_database_url(database_url):
                command.upgrade(config, "head")

            engine = create_engine(database_url)
            try:
                inspector = inspect(engine)
                table_names = set(inspector.get_table_names())
                agent_columns = {column["name"] for column in inspector.get_columns("agent")}
            finally:
                engine.dispose()

            self.assertTrue(EXPECTED_TABLES.issubset(table_names))
            self.assertIn("knowledge_base_id", agent_columns)
            self.assertIn("workflow_id", agent_columns)


if __name__ == "__main__":
    unittest.main()
