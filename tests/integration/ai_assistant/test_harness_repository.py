from contextlib import contextmanager
from collections.abc import Iterator
import unittest

from sqlalchemy.orm import Session

from tests.support.mysql import mysql8_session


class AiAssistantHarnessRepositoryTest(unittest.TestCase):
    def test_run_events_are_persisted_and_replayed_in_sequence(self) -> None:
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository

        with _session() as session:
            repository = AiAssistantRepository(session)
            assistant_session = repository.create_session(title="Kernel test")
            run = repository.create_run(
                session_id=assistant_session["id"],
                user_message="Summarize this",
                idempotency_key="repo-run-1",
            )
            first = repository.append_event(
                run_id=run["id"],
                session_id=assistant_session["id"],
                event_type="run.started",
                visible_title="Run started",
                visible_summary="The assistant run started.",
                payload={"phase": "reason"},
            )
            second = repository.append_event(
                run_id=run["id"],
                session_id=assistant_session["id"],
                event_type="tool.call_completed",
                visible_title="Tool completed",
                visible_summary="echo_context returned output.",
                payload={"toolName": "echo_context"},
            )

            replayed = repository.list_run_events(run["id"])

        self.assertEqual(first["sequence"], 1)
        self.assertEqual(second["sequence"], 2)
        self.assertEqual([event["sequence"] for event in replayed], [1, 2])
        self.assertEqual([event["type"] for event in replayed], ["run.started", "tool.call_completed"])

    def test_tool_call_persistence_records_input_output_status_and_duration(self) -> None:
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository

        with _session() as session:
            repository = AiAssistantRepository(session)
            assistant_session = repository.create_session(title="Tool call test")
            run = repository.create_run(
                session_id=assistant_session["id"],
                user_message="Echo this",
                idempotency_key="repo-run-2",
            )

            tool_call = repository.record_tool_call(
                run_id=run["id"],
                session_id=assistant_session["id"],
                tool_name="echo_context",
                input_payload={"message": "Echo this"},
                output_payload={"echo": "Echo this"},
                status="COMPLETED",
                duration_ms=12,
            )
            listed = repository.list_run_tool_calls(run["id"])

        self.assertEqual(tool_call["tool_name"], "echo_context")
        self.assertEqual(tool_call["status"], "COMPLETED")
        self.assertEqual(tool_call["duration_ms"], 12)
        self.assertEqual(listed[0]["output_payload"]["echo"], "Echo this")

    def test_run_status_claim_is_compare_and_set(self) -> None:
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository

        with _session() as session:
            repository = AiAssistantRepository(session)
            assistant_session = repository.create_session(title="Worker claim test")
            run = repository.create_run(
                session_id=assistant_session["id"],
                user_message="Claim this",
                idempotency_key="repo-run-claim",
            )
            repository.update_run_status(run["id"], "QUEUED")

            claimed = repository.claim_run_status(
                run["id"],
                expected_status="QUEUED",
                next_status="RUNNING",
                input_payload={"sessionRuntime": {"worker": {"leaseToken": "lease-a"}}},
            )
            stale = repository.claim_run_status(
                run["id"],
                expected_status="QUEUED",
                next_status="RUNNING",
                input_payload={"sessionRuntime": {"worker": {"leaseToken": "lease-b"}}},
            )

        self.assertIsNotNone(claimed)
        assert claimed is not None
        self.assertEqual(claimed["status"], "RUNNING")
        self.assertEqual(claimed["input_payload"]["sessionRuntime"]["worker"]["leaseToken"], "lease-a")
        self.assertIsNone(stale)

    def test_complete_run_does_not_overwrite_cancelled_status(self) -> None:
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository

        with _session() as session:
            repository = AiAssistantRepository(session)
            assistant_session = repository.create_session(title="Completion guard test")
            run = repository.create_run(
                session_id=assistant_session["id"],
                user_message="Do not overwrite cancellation",
                idempotency_key="repo-run-complete-guard",
            )
            repository.update_run_status(
                run["id"],
                "CANCELLED",
                response_payload={"finalAnswer": "运行已取消。"},
                completed=True,
            )

            completed = repository.complete_run(run["id"], {"finalAnswer": "late completion"})

        self.assertEqual(completed["status"], "CANCELLED")
        self.assertEqual(completed["response_payload"]["finalAnswer"], "运行已取消。")


@contextmanager
def _session() -> Iterator[Session]:
    from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

    with mysql8_session(
        "ai_assistant_kernel",
        tables=ai_assistant_tables(),
        register=register_ai_assistant_tables,
    ) as session:
        yield session


if __name__ == "__main__":
    unittest.main()
