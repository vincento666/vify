import unittest

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from tests.support.mysql import (
    Mysql8TestDatabase,
    configured_mysql8_database_url,
    mysql8_database_url,
)


class AiAssistantMemoryScopePersistenceTest(unittest.TestCase):
    def test_alembic_upgrade_adds_scope_to_existing_session_and_run_tables(self) -> None:
        with mysql8_database_url("ai_assistant_memory_scope_migration") as database_url:
            config = Config("alembic.ini")
            config.set_main_option("script_location", "alembic")
            config.set_main_option("sqlalchemy.url", database_url)
            with configured_mysql8_database_url(database_url):
                command.upgrade(config, "0031_ai_assistant_tool_circuit_override")

            engine = create_engine(database_url)
            try:
                with engine.begin() as connection:
                    connection.execute(
                        text(
                            "INSERT INTO ai_assistant_session "
                            "(user_id, workspace_id, title, status, context_json, deleted, created_at, updated_at) "
                            "VALUES ('legacy-user', 'legacy-workspace', 'legacy', 'ACTIVE', "
                            "JSON_OBJECT('keep', 'value'), 0, NOW(), NOW())"
                        )
                    )
                    session_indexes = {index["name"] for index in inspect(connection).get_indexes("ai_assistant_session")}
                    run_indexes = {index["name"] for index in inspect(connection).get_indexes("ai_assistant_run")}
                    if "idx_ai_assistant_session_scope" in session_indexes:
                        connection.execute(text("DROP INDEX idx_ai_assistant_session_scope ON ai_assistant_session"))
                    if "idx_ai_assistant_run_scope" in run_indexes:
                        connection.execute(text("DROP INDEX idx_ai_assistant_run_scope ON ai_assistant_run"))
                    connection.execute(text("ALTER TABLE ai_assistant_session DROP COLUMN workspace_id, DROP COLUMN user_id"))
                    connection.execute(text("ALTER TABLE ai_assistant_run DROP COLUMN workspace_id, DROP COLUMN user_id"))

                with configured_mysql8_database_url(database_url):
                    command.upgrade(config, "head")

                inspector = inspect(engine)
                session_columns = {column["name"] for column in inspector.get_columns("ai_assistant_session")}
                run_columns = {column["name"] for column in inspector.get_columns("ai_assistant_run")}
                session_indexes = {index["name"] for index in inspector.get_indexes("ai_assistant_session")}
                run_indexes = {index["name"] for index in inspector.get_indexes("ai_assistant_run")}
                with engine.connect() as connection:
                    migrated_legacy = connection.execute(
                        text(
                            "SELECT user_id, workspace_id, "
                            "JSON_UNQUOTE(JSON_EXTRACT(context_json, '$.keep')) AS kept_value "
                            "FROM ai_assistant_session WHERE title = 'legacy'"
                        )
                    ).mappings().one()
            finally:
                engine.dispose()

        self.assertTrue({"user_id", "workspace_id"}.issubset(session_columns))
        self.assertTrue({"user_id", "workspace_id"}.issubset(run_columns))
        self.assertIn("idx_ai_assistant_session_scope", session_indexes)
        self.assertIn("idx_ai_assistant_run_scope", run_indexes)
        from app.modules.ai_assistant.domain.access_scope import local_ai_assistant_scope

        self.assertEqual(migrated_legacy["user_id"], "local-user")
        self.assertEqual(migrated_legacy["workspace_id"], local_ai_assistant_scope().workspace_id)
        self.assertEqual(migrated_legacy["kept_value"], "value")

    def test_sessions_are_isolated_by_trusted_user_and_workspace_scope(self) -> None:
        from app.modules.ai_assistant.domain.access_scope import AiAssistantAccessScope
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository
        from app.modules.ai_assistant.infra.schema import (
            ai_assistant_tables,
            register_ai_assistant_tables,
        )

        with Mysql8TestDatabase("ai_assistant_memory_scope") as database:
            database.create_all(
                tables=ai_assistant_tables(),
                register=register_ai_assistant_tables,
            )
            with database.session() as session:
                alice_scope = AiAssistantAccessScope(
                    user_id="alice",
                    workspace_id="workspace-a",
                )
                alice = AiAssistantRepository(session, access_scope=alice_scope)
                created = alice.create_session(title="Alice private session")

                bob = AiAssistantRepository(
                    session,
                    access_scope=AiAssistantAccessScope(
                        user_id="bob",
                        workspace_id="workspace-a",
                    ),
                )
                alice_other_workspace = AiAssistantRepository(
                    session,
                    access_scope=AiAssistantAccessScope(
                        user_id="alice",
                        workspace_id="workspace-b",
                    ),
                )

                self.assertEqual(created["user_id"], "alice")
                self.assertEqual(created["workspace_id"], "workspace-a")
                self.assertEqual(bob.list_sessions(), [])
                self.assertIsNone(bob.get_session(created["id"]))
                self.assertFalse(bob.delete_session(created["id"]))
                with self.assertRaises(KeyError):
                    bob.create_run(
                        session_id=created["id"],
                        user_message="foreign run",
                        idempotency_key="foreign-run",
                    )
                alice_run = alice.create_run(
                    session_id=created["id"],
                    user_message="owned run",
                    idempotency_key="owned-run",
                )
                with self.assertRaises(KeyError):
                    bob.update_run_status(alice_run["id"], "FAILED")
                self.assertEqual(alice.get_run(alice_run["id"])["status"], "RUNNING")
                self.assertEqual(alice_other_workspace.list_sessions(), [])
                self.assertIsNone(alice_other_workspace.get_session(created["id"]))
                self.assertIsNotNone(alice.get_session(created["id"]))


if __name__ == "__main__":
    unittest.main()
