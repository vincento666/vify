import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import date, datetime, timedelta
import tempfile
import time
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from tests.support.mysql import Mysql8TestDatabase, configured_mysql8_database_url, mysql8_database_url


class AiAssistantMemoryExtractionCursorTest(unittest.TestCase):
    def test_cross_process_style_claim_waits_for_scope_lock_then_sees_third_run(self) -> None:
        from app.modules.ai_assistant.domain.access_scope import AiAssistantAccessScope
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        with Mysql8TestDatabase("ai_assistant_memory_extraction_waiting_claim") as database:
            database.create_all(tables=ai_assistant_tables(), register=register_ai_assistant_tables)
            scope = AiAssistantAccessScope(user_id="alice", workspace_id="workspace-a")
            with database.session() as session:
                repository = AiAssistantRepository(session, access_scope=scope)
                assistant_session = repository.create_session(title="waiting claim")
                for index in range(3):
                    self._complete_run(repository, assistant_session["id"], f"waiting-{index}")
                lock_name = repository._memory_extraction_lock_name()
                engine = session.get_bind()

            with engine.connect() as holder:
                self.assertEqual(
                    holder.execute(
                        text("SELECT GET_LOCK(:name, 0)"),
                        {"name": lock_name},
                    ).scalar_one(),
                    1,
                )

                def claim() -> dict | None:
                    with database.session() as session:
                        return AiAssistantRepository(
                            session,
                            access_scope=scope,
                        ).claim_memory_extraction_batch()

                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(claim)
                    time.sleep(0.1)
                    self.assertFalse(future.done())
                    self.assertEqual(
                        holder.execute(
                            text("SELECT RELEASE_LOCK(:name)"),
                            {"name": lock_name},
                        ).scalar_one(),
                        1,
                    )
                    claimed = future.result(timeout=3)

            self.assertIsNotNone(claimed)
            self.assertEqual(len(claimed["run_ids"]), 3)

    def test_independent_connections_claim_once_and_release_scope_lock(self) -> None:
        from app.modules.ai_assistant.domain.access_scope import AiAssistantAccessScope
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        with Mysql8TestDatabase("ai_assistant_memory_extraction_concurrent_claim") as database:
            database.create_all(tables=ai_assistant_tables(), register=register_ai_assistant_tables)
            scope = AiAssistantAccessScope(user_id="alice", workspace_id="workspace-a")
            with database.session() as session:
                repository = AiAssistantRepository(session, access_scope=scope)
                assistant_session = repository.create_session(title="concurrent claim")
                for index in range(3):
                    self._complete_run(repository, assistant_session["id"], f"claim-{index}")

            def claim() -> dict | None:
                with database.session() as session:
                    return AiAssistantRepository(
                        session,
                        access_scope=scope,
                    ).claim_memory_extraction_batch()

            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(lambda _: claim(), range(2)))

            claimed = [result for result in results if result is not None]
            self.assertEqual(len(claimed), 1)
            with database.session() as session:
                session.execute(
                    text(
                        "UPDATE ai_assistant_memory_cursor "
                        "SET lease_expires_at = :expired WHERE pending_batch_key = :batch_key"
                    ),
                    {
                        "expired": datetime.now() - timedelta(seconds=1),
                        "batch_key": claimed[0]["batch_key"],
                    },
                )
                session.commit()
            reclaimed = claim()
            self.assertIsNotNone(reclaimed)
            self.assertEqual(reclaimed["batch_key"], claimed[0]["batch_key"])

    def test_atomic_write_failure_keeps_cursor_pending_and_retries_without_loss(self) -> None:
        from app.modules.ai_assistant.domain.access_scope import AiAssistantAccessScope
        from app.modules.ai_assistant.domain.markdown_memory import MarkdownMemoryStore, MemoryScopeResolver
        from app.modules.ai_assistant.domain.memory_extraction import MemoryExtractionCoordinator
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        with (
            Mysql8TestDatabase("ai_assistant_memory_extraction_write_retry") as database,
            tempfile.TemporaryDirectory() as memory_root,
        ):
            database.create_all(tables=ai_assistant_tables(), register=register_ai_assistant_tables)
            access_scope = AiAssistantAccessScope(user_id="alice", workspace_id="workspace-a")

            @contextmanager
            def repository_factory():
                with database.session() as session:
                    yield AiAssistantRepository(session, access_scope=access_scope)

            with repository_factory() as repository:
                assistant_session = repository.create_session(title="write retry")
                runs = [
                    self._complete_run(repository, assistant_session["id"], f"write-{index}")
                    for index in range(3)
                ]
            resolver = MemoryScopeResolver(memory_root)
            try:
                memory_scope = resolver.resolve(
                    trusted_user_id="alice",
                    trusted_workspace_id="workspace-a",
                )
                store = MarkdownMemoryStore(resolver)
                extractor = _ScriptedExtractor(
                    [
                        ["First uncommitted model fact."],
                        ["Second retry model fact."],
                    ]
                )
                coordinator = MemoryExtractionCoordinator(
                    repository_factory=repository_factory,
                    store=store,
                    scope=memory_scope,
                    extractor=extractor,
                    today=lambda: date(2026, 7, 11),
                )
                with patch.object(store, "replace_planned", side_effect=OSError("write failed")):
                    failed = coordinator.process_one()

                with repository_factory() as repository:
                    pending = repository.get_memory_extraction_cursor()
                    self.assertEqual(pending["last_processed_run_id"], 0)
                    self.assertIsNotNone(pending["pending_target_hash"])
                    self.assertTrue(
                        all(repository.get_run(run["id"])["status"] == "COMPLETED" for run in runs)
                    )
                self.assertEqual(store.read_recent(memory_scope, today=date(2026, 7, 11)).content, "")

                retried = coordinator.process_one()
                content = store.read_recent(memory_scope, today=date(2026, 7, 11)).content

                self.assertEqual(failed.status, "FAILED")
                self.assertEqual(retried.status, "COMPLETED")
                self.assertEqual(extractor.calls, 2)
                self.assertNotIn("First uncommitted model fact.", content)
                self.assertEqual(content.count("Second retry model fact."), 1)
            finally:
                resolver.close()

    def test_alembic_head_creates_operational_cursor_without_memory_text_columns(self) -> None:
        with mysql8_database_url("ai_assistant_memory_cursor_migration") as database_url:
            config = Config("alembic.ini")
            config.set_main_option("script_location", "alembic")
            config.set_main_option("sqlalchemy.url", database_url)
            with configured_mysql8_database_url(database_url):
                command.upgrade(config, "0032_ai_assistant_memory_scope")
            engine = create_engine(database_url)
            try:
                from app.modules.ai_assistant.infra.repository import AiAssistantRepository

                with Session(engine) as session:
                    repository = AiAssistantRepository(session)
                    assistant_session = repository.create_session(title="migration-backfill")
                    completed_run = self._complete_run(
                        repository,
                        assistant_session["id"],
                        "migration-backfill",
                    )
                with engine.begin() as connection:
                    table_names = set(inspect(connection).get_table_names())
                    if "ai_assistant_memory_cursor" in table_names:
                        connection.execute(text("DROP TABLE ai_assistant_memory_cursor"))
                    if "ai_assistant_memory_completion" in table_names:
                        connection.execute(text("DROP TABLE ai_assistant_memory_completion"))
                with configured_mysql8_database_url(database_url):
                    command.upgrade(config, "head")
                columns = {
                    column["name"]
                    for column in inspect(engine).get_columns("ai_assistant_memory_cursor")
                }
                completion_columns = {
                    column["name"]
                    for column in inspect(engine).get_columns("ai_assistant_memory_completion")
                }
                with engine.connect() as connection:
                    backfilled_run_ids = set(
                        connection.execute(
                            text("SELECT run_id FROM ai_assistant_memory_completion")
                        ).scalars()
                    )
            finally:
                engine.dispose()

        self.assertTrue(
            {
                "user_id",
                "workspace_id",
                "last_processed_run_id",
                "last_processed_completion_id",
                "pending_completion_ids",
                "pending_run_ids",
                "pending_batch_key",
                "pending_source_hash",
                "pending_input_hash",
                "pending_target_hash",
                "claim_token",
                "lease_expires_at",
                "status",
                "last_error",
            }.issubset(columns)
        )
        self.assertTrue({"memory", "facts", "content"}.isdisjoint(columns))
        self.assertTrue({"user_id", "workspace_id", "run_id", "completed_at"}.issubset(completion_columns))
        self.assertIn(completed_run["id"], backfilled_run_ids)

    def test_retry_after_file_write_recovers_cursor_without_reextracting(self) -> None:
        from app.modules.ai_assistant.domain.access_scope import AiAssistantAccessScope
        from app.modules.ai_assistant.domain.markdown_memory import MarkdownMemoryStore, MemoryScopeResolver
        from app.modules.ai_assistant.domain.memory_extraction import MemoryExtractionCoordinator
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        with (
            Mysql8TestDatabase("ai_assistant_memory_extraction_recovery") as database,
            tempfile.TemporaryDirectory() as memory_root,
        ):
            database.create_all(tables=ai_assistant_tables(), register=register_ai_assistant_tables)
            access_scope = AiAssistantAccessScope(user_id="alice", workspace_id="workspace-a")

            @contextmanager
            def repository_factory():
                with database.session() as session:
                    yield AiAssistantRepository(session, access_scope=access_scope)

            with repository_factory() as repository:
                assistant_session = repository.create_session(title="recovery")
                runs = [
                    self._complete_run(repository, assistant_session["id"], f"recovery-{index}")
                    for index in range(3)
                ]
            resolver = MemoryScopeResolver(memory_root)
            try:
                memory_scope = resolver.resolve(
                    trusted_user_id="alice",
                    trusted_workspace_id="workspace-a",
                )
                store = MarkdownMemoryStore(resolver)
                extractor = _FakeExtractor(["Crash recovery stays idempotent."])
                coordinator = MemoryExtractionCoordinator(
                    repository_factory=repository_factory,
                    store=store,
                    scope=memory_scope,
                    extractor=extractor,
                    today=lambda: date(2026, 7, 11),
                )
                with patch.object(
                    AiAssistantRepository,
                    "complete_memory_extraction_batch",
                    side_effect=RuntimeError("crash before cursor completion"),
                ):
                    failed = coordinator.process_one()

                retry_extractor = _FailIfCalledExtractor()
                recovered = MemoryExtractionCoordinator(
                    repository_factory=repository_factory,
                    store=store,
                    scope=memory_scope,
                    extractor=retry_extractor,
                    today=lambda: date(2026, 7, 11),
                ).process_one()

                self.assertEqual(failed.status, "FAILED")
                self.assertEqual(recovered.status, "RECOVERED")
                self.assertEqual(retry_extractor.calls, 0)
                with repository_factory() as repository:
                    cursor = repository.get_memory_extraction_cursor()
                    self.assertEqual(cursor["last_processed_run_id"], runs[-1]["id"])
                    self.assertEqual(cursor["status"], "IDLE")
                content = store.read_recent(memory_scope, today=date(2026, 7, 11)).content
                self.assertEqual(content.count("Crash recovery stays idempotent."), 1)
            finally:
                resolver.close()

    def test_coordinator_extracts_and_commits_memory_after_third_completed_run(self) -> None:
        from app.modules.ai_assistant.domain.access_scope import AiAssistantAccessScope
        from app.modules.ai_assistant.domain.markdown_memory import MarkdownMemoryStore, MemoryScopeResolver
        from app.modules.ai_assistant.domain.memory_extraction import MemoryExtractionCoordinator
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        with (
            Mysql8TestDatabase("ai_assistant_memory_extraction_coordinator") as database,
            tempfile.TemporaryDirectory() as memory_root,
        ):
            database.create_all(tables=ai_assistant_tables(), register=register_ai_assistant_tables)
            resolver = MemoryScopeResolver(memory_root)
            try:
                memory_scope = resolver.resolve(
                    trusted_user_id="alice",
                    trusted_workspace_id="workspace-a",
                )
                store = MarkdownMemoryStore(resolver)
                extractor = _FakeExtractor(["Prefer concise Chinese output."])

                @contextmanager
                def repository_factory():
                    with database.session() as repository_session:
                        yield AiAssistantRepository(
                            repository_session,
                            access_scope=AiAssistantAccessScope(
                                user_id="alice",
                                workspace_id="workspace-a",
                            ),
                        )

                with database.session() as session:
                    repository = AiAssistantRepository(
                        session,
                        access_scope=AiAssistantAccessScope(
                            user_id="alice",
                            workspace_id="workspace-a",
                        ),
                    )
                    first_session = repository.create_session(title="first")
                    second_session = repository.create_session(title="second")
                    delayed = repository.create_run(
                        session_id=first_session["id"],
                        user_message="delayed",
                        idempotency_key="run-delayed",
                    )
                    first = self._complete_run(repository, first_session["id"], "first")
                    second = self._complete_run(repository, second_session["id"], "second")
                    coordinator = MemoryExtractionCoordinator(
                        repository_factory=repository_factory,
                        store=store,
                        scope=memory_scope,
                        extractor=extractor,
                        today=lambda: date(2026, 7, 11),
                    )

                    self.assertEqual(coordinator.process_one().status, "PENDING")
                    third = self._complete_run(repository, first_session["id"], "third")
                    result = coordinator.process_one()

                    self.assertEqual(result.status, "COMPLETED")
                    self.assertEqual(result.run_ids, (first["id"], second["id"], third["id"]))
                    self.assertEqual(extractor.calls, 1)
                    window = store.read_recent(memory_scope, today=date(2026, 7, 11))
                    self.assertIn("Prefer concise Chinese output.", window.content)
                    with repository_factory() as inspection_repository:
                        cursor = inspection_repository.get_memory_extraction_cursor()
                    self.assertEqual(cursor["last_processed_run_id"], third["id"])
                    self.assertIsNone(cursor["pending_batch_key"])
                    self.assertEqual(cursor["status"], "IDLE")

                    repository.complete_run(
                        delayed["id"],
                        {"finalAnswer": "answer-delayed", "toolCalls": []},
                    )
                    fourth = self._complete_run(repository, second_session["id"], "fourth")
                    fifth = self._complete_run(repository, first_session["id"], "fifth")
                    late_batch = coordinator.process_one()
                    self.assertEqual(
                        late_batch.run_ids,
                        (delayed["id"], fourth["id"], fifth["id"]),
                    )
                    self.assertEqual(extractor.last_run_ids, list(late_batch.run_ids))
                    self.assertEqual(extractor.calls, 2)
            finally:
                resolver.close()

    def test_three_completed_runs_across_sessions_claim_one_durable_scoped_batch(self) -> None:
        from app.modules.ai_assistant.domain.access_scope import AiAssistantAccessScope
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        with Mysql8TestDatabase("ai_assistant_memory_extraction_cursor") as database:
            database.create_all(tables=ai_assistant_tables(), register=register_ai_assistant_tables)
            with database.session() as session:
                scope = AiAssistantAccessScope(user_id="alice", workspace_id="workspace-a")
                repository = AiAssistantRepository(session, access_scope=scope)
                first_session = repository.create_session(title="first")
                second_session = repository.create_session(title="second")

                first = self._complete_run(repository, first_session["id"], "first")
                for terminal_status in ("FAILED", "CANCELLED", "DENIED"):
                    excluded = repository.create_run(
                        session_id=first_session["id"],
                        user_message=terminal_status.lower(),
                        idempotency_key=f"excluded-{terminal_status.lower()}",
                    )
                    repository.complete_run(
                        excluded["id"],
                        {"finalAnswer": terminal_status.lower()},
                        status=terminal_status,
                    )
                repository.create_run(
                    session_id=first_session["id"],
                    user_message="interrupted",
                    idempotency_key="excluded-interrupted",
                )
                second = self._complete_run(repository, second_session["id"], "second")
                self.assertIsNone(repository.claim_memory_extraction_batch())

                third = self._complete_run(repository, first_session["id"], "third")
                batch = repository.claim_memory_extraction_batch()
                concurrent_claim = repository.claim_memory_extraction_batch()
                repository.record_memory_extraction_target(
                    batch_key=batch["batch_key"],
                    source_hash=batch["source_hash"],
                    input_hash="test-input-hash",
                    target_hash="test-target-hash",
                    claim_token=batch["claim_token"],
                )
                session.execute(
                    text(
                        "UPDATE ai_assistant_memory_cursor "
                        "SET lease_expires_at = :expired WHERE pending_batch_key = :batch_key"
                    ),
                    {
                        "expired": datetime.now() - timedelta(seconds=1),
                        "batch_key": batch["batch_key"],
                    },
                )
                session.commit()
                reclaimed = repository.claim_memory_extraction_batch()

                bob = AiAssistantRepository(
                    session,
                    access_scope=AiAssistantAccessScope(user_id="bob", workspace_id="workspace-a"),
                )

                self.assertIsNotNone(batch)
                self.assertEqual(batch["run_ids"], [first["id"], second["id"], third["id"]])
                self.assertEqual(batch["status"], "EXTRACTING")
                self.assertIsNone(concurrent_claim)
                self.assertEqual(reclaimed["batch_key"], batch["batch_key"])
                self.assertEqual(reclaimed["source_hash"], batch["source_hash"])
                self.assertEqual(reclaimed["input_hash"], "test-input-hash")
                self.assertNotEqual(reclaimed["claim_token"], batch["claim_token"])
                stale_write_calls: list[str] = []
                with self.assertRaisesRegex(RuntimeError, "claim"):
                    repository.commit_memory_extraction_plan(
                        batch_key=batch["batch_key"],
                        source_hash=batch["source_hash"],
                        input_hash="stale-input-hash",
                        target_hash="stale-target-hash",
                        claim_token=batch["claim_token"],
                        write=lambda: stale_write_calls.append("wrote"),
                    )
                self.assertEqual(stale_write_calls, [])
                with self.assertRaisesRegex(RuntimeError, "claim"):
                    repository.complete_memory_extraction_batch(
                        batch_key=batch["batch_key"],
                        target_hash="test-target-hash",
                        claim_token=batch["claim_token"],
                    )
                self.assertIsNone(bob.claim_memory_extraction_batch())

                cursor = repository.get_memory_extraction_cursor()
                self.assertEqual(cursor["pending_run_ids"], batch["run_ids"])
                self.assertEqual(cursor["last_processed_run_id"], 0)
                self.assertNotIn("memory", cursor)
                self.assertNotIn("facts", cursor)

    @staticmethod
    def _complete_run(repository, session_id: int, message: str) -> dict:
        run = repository.create_run(
            session_id=session_id,
            user_message=message,
            idempotency_key=f"run-{message}",
        )
        return repository.complete_run(
            run["id"],
            {"finalAnswer": f"answer-{message}", "toolCalls": []},
        )


if __name__ == "__main__":
    unittest.main()


class _FakeExtractor:
    def __init__(self, facts: list[str]) -> None:
        self._facts = facts
        self.calls = 0

    def extract(self, runs: list[dict]) -> list[str]:
        self.calls += 1
        self.last_run_ids = [run["id"] for run in runs]
        return list(self._facts)


class _FailIfCalledExtractor:
    def __init__(self) -> None:
        self.calls = 0

    def extract(self, runs: list[dict]) -> list[str]:
        self.calls += 1
        raise AssertionError("extractor must not run after target file already matches")


class _ScriptedExtractor:
    def __init__(self, facts_by_call: list[list[str]]) -> None:
        self._facts_by_call = facts_by_call
        self.calls = 0

    def extract(self, runs: list[dict]) -> list[str]:
        facts = self._facts_by_call[self.calls]
        self.calls += 1
        return list(facts)
