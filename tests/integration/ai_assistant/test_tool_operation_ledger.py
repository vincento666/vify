import unittest

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from tests.support.mysql import Mysql8TestDatabase, configured_mysql8_database_url, mysql8_database_url


class ToolOperationLedgerRepositoryTest(unittest.TestCase):
    def test_alembic_head_creates_operation_and_attempt_tables(self) -> None:
        with mysql8_database_url("ai_assistant_tool_operation_migration") as database_url:
            config = Config("alembic.ini")
            config.set_main_option("script_location", "alembic")
            config.set_main_option("sqlalchemy.url", database_url)

            with configured_mysql8_database_url(database_url):
                command.upgrade(config, "head")

            engine = create_engine(database_url)
            try:
                inspector = inspect(engine)
                table_names = set(inspector.get_table_names())
                operation_columns = {column["name"] for column in inspector.get_columns("ai_assistant_tool_operation")}
                attempt_columns = {column["name"] for column in inspector.get_columns("ai_assistant_tool_attempt")}
            finally:
                engine.dispose()

        self.assertIn("ai_assistant_tool_operation", table_names)
        self.assertIn("ai_assistant_tool_attempt", table_names)
        self.assertTrue({"operation_id", "session_id", "run_id", "status"}.issubset(operation_columns))
        self.assertTrue({"operation_id", "attempt_id", "adapter_name", "status"}.issubset(attempt_columns))

    def test_operation_and_attempt_survive_new_repository_instance(self) -> None:
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository

        with Mysql8TestDatabase("ai_assistant_tool_operation_ledger") as database:
            from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

            database.create_all(tables=ai_assistant_tables(), register=register_ai_assistant_tables)
            with database.session() as session:
                repository = AiAssistantRepository(session)
                assistant_session = repository.create_session(title="Durable tool operation")
                run = repository.create_run(
                    session_id=int(assistant_session["id"]),
                    user_message="Send one side effect",
                    idempotency_key="ledger-run-1",
                )
                operation = repository.create_tool_operation(
                    operation_id="op-ledger-1",
                    session_id=int(assistant_session["id"]),
                    run_id=int(run["id"]),
                    plan_step_id="send-message",
                    tool_name="side_effect_tool",
                    effect_class="SIDE_EFFECT",
                    idempotency_key="effect-ledger-1",
                    request_hash="request-hash-1",
                )
                repository.create_tool_attempt(
                    operation_id=operation["operation_id"],
                    attempt_id="attempt-ledger-1",
                    adapter_name="primary",
                    status="DISPATCHED",
                    request_hash="attempt-request-hash-1",
                )

            with database.session() as restarted_session:
                restarted = AiAssistantRepository(restarted_session)
                loaded_operation = restarted.get_tool_operation("op-ledger-1")
                loaded_attempts = restarted.list_tool_attempts("op-ledger-1")

        self.assertEqual(loaded_operation["operation_id"], "op-ledger-1")
        self.assertEqual(loaded_operation["session_id"], assistant_session["id"])
        self.assertEqual(loaded_operation["run_id"], run["id"])
        self.assertEqual(loaded_operation["status"], "PENDING")
        self.assertEqual(loaded_operation["request_hash"], "request-hash-1")
        self.assertEqual([row["attempt_id"] for row in loaded_attempts], ["attempt-ledger-1"])
        self.assertEqual(loaded_attempts[0]["status"], "DISPATCHED")

    def test_operation_claim_and_attempt_update_need_no_event_sequence(self) -> None:
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository

        with Mysql8TestDatabase("ai_assistant_tool_operation_claim") as database:
            from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

            database.create_all(tables=ai_assistant_tables(), register=register_ai_assistant_tables)
            with database.session() as session:
                repository = AiAssistantRepository(session)
                assistant_session = repository.create_session(title="Claim durable operation")
                run = repository.create_run(
                    session_id=int(assistant_session["id"]),
                    user_message="Claim one operation",
                    idempotency_key="ledger-run-claim",
                )
                repository.create_tool_operation(
                    operation_id="op-claim-1",
                    session_id=int(assistant_session["id"]),
                    run_id=int(run["id"]),
                    plan_step_id="claim-step",
                    tool_name="side_effect_tool",
                    effect_class="SIDE_EFFECT",
                    idempotency_key="effect-claim-1",
                    request_hash="request-hash-claim",
                )
                attempt = repository.create_tool_attempt(
                    operation_id="op-claim-1",
                    attempt_id="attempt-claim-1",
                    adapter_name="primary",
                    status="PENDING",
                    request_hash="attempt-request-hash-claim",
                )

                claimed = repository.claim_tool_operation(
                    "op-claim-1", expected_status="PENDING", next_status="DISPATCHED"
                )
                stale = repository.claim_tool_operation(
                    "op-claim-1", expected_status="PENDING", next_status="DISPATCHED"
                )
                updated_attempt = repository.update_tool_attempt(
                    attempt["attempt_id"], status="COMPLETED", response_hash="response-hash-claim"
                )

        self.assertEqual(claimed["status"], "DISPATCHED")
        self.assertIsNone(stale)
        self.assertEqual(updated_attempt["status"], "COMPLETED")
        self.assertEqual(updated_attempt["response_hash"], "response-hash-claim")


if __name__ == "__main__":
    unittest.main()
