import unittest
import time

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
                release_columns = {
                    column["name"] for column in inspector.get_columns("ai_assistant_tool_operation_release")
                }
            finally:
                engine.dispose()

        self.assertIn("ai_assistant_tool_operation", table_names)
        self.assertIn("ai_assistant_tool_attempt", table_names)
        self.assertIn("ai_assistant_tool_operation_release", table_names)
        self.assertTrue(
            {"operation_id", "session_id", "run_id", "status", "output_payload", "retention_until"}.issubset(
                operation_columns
            )
        )
        self.assertTrue({"operation_id", "attempt_id", "adapter_name", "status"}.issubset(attempt_columns))
        self.assertTrue(
            {"operation_id", "authority", "actor", "evidence_ref", "previous_status", "next_status"}.issubset(
                release_columns
            )
        )

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

    def test_completed_side_effect_replays_after_tool_runner_restart(self) -> None:
        from app.modules.ai_assistant.domain.tool_runtime import ToolRunner, ToolRunnerPolicy
        from app.modules.ai_assistant.domain.tools import RiskLevel, ToolManifest, ToolRegistry, ToolResult
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository

        calls: list[dict[str, object]] = []
        pre_dispatch_operations: list[dict[str, object] | None] = []
        ledger_holder: dict[str, AiAssistantRepository] = {}

        def send(payload: dict[str, object]) -> ToolResult:
            calls.append(payload)
            runtime = dict(payload["_toolRuntime"])
            pre_dispatch_operations.append(ledger_holder["repository"].get_tool_operation(str(runtime["operationId"])))
            return ToolResult(status="COMPLETED", output={"sent": True})

        manifest = ToolManifest(
            name="send_tool",
            description="side-effect test tool",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            timeout_ms=100,
            risk_level=RiskLevel.BUSINESS_WRITE,
            read_resources=[],
            write_resources=["test:send"],
            policy_ref="test_side_effect",
        )
        registry = ToolRegistry({"send_tool": (manifest, send)})

        with Mysql8TestDatabase("ai_assistant_tool_operation_replay") as database:
            from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

            database.create_all(tables=ai_assistant_tables(), register=register_ai_assistant_tables)
            with database.session() as session:
                repository = AiAssistantRepository(session)
                ledger_holder["repository"] = repository
                assistant_session = repository.create_session(title="Durable side effect")
                run = repository.create_run(
                    session_id=int(assistant_session["id"]),
                    user_message="Send only once",
                    idempotency_key="side-effect-run-1",
                )
                payload = {
                    "caseId": "case-side-effect-1",
                    "details": {"z": 2, "a": 1},
                    "_aiAssistantRuntime": {
                        "sessionId": int(assistant_session["id"]),
                        "runId": int(run["id"]),
                        "planStepId": "send-step-1",
                    },
                }
                first = ToolRunner(
                    registry,
                    policy=ToolRunnerPolicy(max_attempts=1),
                    operation_ledger=repository,
                ).run("send_tool", payload, idempotency_key="side-effect-key-1")

            with database.session() as restarted_session:
                restarted_payload = {
                    "details": {"a": 1, "z": 2},
                    "caseId": "case-side-effect-1",
                    "_aiAssistantRuntime": {
                        "runId": int(run["id"]),
                        "planStepId": "send-step-1",
                        "sessionId": int(assistant_session["id"]),
                    },
                }
                second = ToolRunner(
                    registry,
                    policy=ToolRunnerPolicy(max_attempts=1),
                    operation_ledger=AiAssistantRepository(restarted_session),
                ).run("send_tool", restarted_payload, idempotency_key="side-effect-key-1")

        self.assertEqual(first.tool_result.output, {"sent": True})
        self.assertEqual(second.tool_result.output, {"sent": True})
        self.assertEqual(first.operation_id, second.operation_id)
        self.assertEqual(len(calls), 1)
        self.assertEqual(pre_dispatch_operations[0]["status"], "PENDING")
        self.assertEqual(pre_dispatch_operations[0]["idempotency_key"], "side-effect-key-1")

    def test_side_effect_timeout_becomes_durable_unknown_and_blocks_restart_replay(self) -> None:
        from app.modules.ai_assistant.domain.tool_runtime import ToolRunner, ToolRunnerPolicy
        from app.modules.ai_assistant.domain.tools import RiskLevel, ToolManifest, ToolRegistry, ToolResult
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository

        calls: list[dict[str, object]] = []

        def slow(payload: dict[str, object]) -> ToolResult:
            calls.append(payload)
            time.sleep(0.05)
            return ToolResult(status="COMPLETED", output={"late": True})

        manifest = ToolManifest(
            name="slow_side_effect",
            description="ambiguous side-effect test tool",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            timeout_ms=1,
            risk_level=RiskLevel.BUSINESS_WRITE,
            read_resources=[],
            write_resources=["test:slow"],
            policy_ref="test_side_effect",
        )
        registry = ToolRegistry({"slow_side_effect": (manifest, slow)})

        with Mysql8TestDatabase("ai_assistant_tool_operation_unknown") as database:
            from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

            database.create_all(tables=ai_assistant_tables(), register=register_ai_assistant_tables)
            with database.session() as session:
                repository = AiAssistantRepository(session)
                assistant_session = repository.create_session(title="Unknown side effect")
                run = repository.create_run(
                    session_id=int(assistant_session["id"]),
                    user_message="Do not replay uncertain effect",
                    idempotency_key="unknown-run-1",
                )
                payload = {
                    "caseId": "case-unknown-1",
                    "_aiAssistantRuntime": {
                        "sessionId": int(assistant_session["id"]),
                        "runId": int(run["id"]),
                        "planStepId": "unknown-step-1",
                    },
                }
                first = ToolRunner(
                    registry,
                    policy=ToolRunnerPolicy(max_attempts=1),
                    operation_ledger=repository,
                ).run("slow_side_effect", payload, idempotency_key="unknown-key-1")
                operation = repository.get_tool_operation(first.operation_id)
                attempts = repository.list_tool_attempts(first.operation_id)

            with database.session() as restarted_session:
                second = ToolRunner(
                    registry,
                    policy=ToolRunnerPolicy(max_attempts=1),
                    operation_ledger=AiAssistantRepository(restarted_session),
                ).run("slow_side_effect", payload, idempotency_key="unknown-key-1")

        self.assertEqual(first.tool_result.output["error"]["code"], "TOOL_TIMEOUT")
        self.assertEqual(operation["status"], "UNKNOWN")
        self.assertGreater(operation["retention_until"], operation["updated_at"])
        self.assertEqual(attempts[0]["status"], "UNKNOWN")
        self.assertEqual(second.tool_result.output["error"]["code"], "TOOL_IDEMPOTENCY_UNCERTAIN")
        self.assertEqual(len(calls), 1)

    def test_unknown_release_rejects_model_and_audits_operator_transition(self) -> None:
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository

        with Mysql8TestDatabase("ai_assistant_tool_operation_release") as database:
            from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

            database.create_all(tables=ai_assistant_tables(), register=register_ai_assistant_tables)
            with database.session() as session:
                repository = AiAssistantRepository(session)
                assistant_session = repository.create_session(title="Release unknown operation")
                run = repository.create_run(
                    session_id=int(assistant_session["id"]),
                    user_message="Reconcile unknown effect",
                    idempotency_key="release-run-1",
                )
                repository.create_tool_operation(
                    operation_id="op-release-1",
                    session_id=int(assistant_session["id"]),
                    run_id=int(run["id"]),
                    plan_step_id="release-step",
                    tool_name="side_effect_tool",
                    effect_class="SIDE_EFFECT",
                    idempotency_key="release-key-1",
                    request_hash="release-request-hash",
                )
                repository.mark_tool_operation_unknown("op-release-1", retention_until=run["created_at"])

                with self.assertRaises(PermissionError):
                    repository.release_tool_operation(
                        "op-release-1",
                        authority="model",
                        actor="planner",
                        reason="model guesses success",
                        evidence_ref="model-output",
                        next_status="SUCCEEDED",
                    )
                released = repository.release_tool_operation(
                    "op-release-1",
                    authority="operator",
                    actor="operator-1",
                    reason="remote receipt verified",
                    evidence_ref="receipt:abc123",
                    next_status="SUCCEEDED",
                )
                releases = repository.list_tool_operation_releases("op-release-1")
                audit_export = repository.export_tool_operation_audit("op-release-1")

        self.assertEqual(released["status"], "SUCCEEDED")
        self.assertEqual(len(releases), 1)
        self.assertEqual(releases[0]["authority"], "operator")
        self.assertEqual(releases[0]["actor"], "operator-1")
        self.assertEqual(releases[0]["previous_status"], "UNKNOWN")
        self.assertEqual(releases[0]["next_status"], "SUCCEEDED")
        self.assertEqual(releases[0]["evidence_ref"], "receipt:abc123")
        self.assertEqual(audit_export["releases"][0]["actor"], "operator-1")


if __name__ == "__main__":
    unittest.main()
