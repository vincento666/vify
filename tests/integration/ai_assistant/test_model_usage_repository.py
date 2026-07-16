import unittest
from contextlib import contextmanager
from datetime import date
from datetime import datetime
import json
import tempfile
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from tests.support.mysql import (
    Mysql8TestDatabase,
    configured_mysql8_database_url,
    mysql8_database_url,
)


class AiAssistantModelUsageRepositoryTest(unittest.TestCase):
    def test_alembic_head_creates_scoped_per_call_ledger(self) -> None:
        with mysql8_database_url("ai_assistant_model_usage_migration") as database_url:
            config = Config("alembic.ini")
            config.set_main_option("script_location", "alembic")
            config.set_main_option("sqlalchemy.url", database_url)
            with configured_mysql8_database_url(database_url):
                command.upgrade(config, "head")
            engine = create_engine(database_url)
            try:
                columns = {
                    column["name"]
                    for column in inspect(engine).get_columns("ai_assistant_model_usage")
                }
                unique_constraints = {
                    tuple(constraint["column_names"])
                    for constraint in inspect(engine).get_unique_constraints(
                        "ai_assistant_model_usage"
                    )
                }
            finally:
                engine.dispose()

        self.assertTrue(
            {
                "user_id",
                "workspace_id",
                "session_id",
                "run_id",
                "call_id",
                "call_kind",
                "provider",
                "model",
                "input_tokens",
                "output_tokens",
                "cache_read_tokens",
                "cache_write_tokens",
                "reasoning_tokens",
                "total_tokens",
                "usage_source",
                "provider_cost_usd",
                "estimated_cost_usd",
                "effective_cost_usd",
                "cost_source",
                "pricing_version",
                "started_at",
                "completed_at",
            }.issubset(columns)
        )
        self.assertIn(("user_id", "workspace_id", "run_id", "call_id"), unique_constraints)

    def test_memory_extractor_usage_is_attributed_to_third_run(self) -> None:
        from app.modules.ai_assistant.domain.access_scope import AiAssistantAccessScope
        from app.modules.ai_assistant.domain.live_model import LivePlannerConfig
        from app.modules.ai_assistant.domain.markdown_memory import MarkdownMemoryStore, MemoryScopeResolver
        from app.modules.ai_assistant.domain.memory_extraction import (
            MemoryExtractionCoordinator,
            ModelMemoryExtractor,
        )
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        with (
            Mysql8TestDatabase("ai_assistant_memory_extractor_usage") as database,
            tempfile.TemporaryDirectory() as memory_root,
        ):
            database.create_all(tables=ai_assistant_tables(), register=register_ai_assistant_tables)
            scope = AiAssistantAccessScope("alice", "workspace-a")

            @contextmanager
            def repository_factory():
                with database.session() as session:
                    yield AiAssistantRepository(session, access_scope=scope)

            with repository_factory() as repository:
                assistant_session = repository.create_session(title="memory usage")
                runs = []
                for index in range(3):
                    run = repository.create_run(
                        session_id=assistant_session["id"],
                        user_message=f"memory-{index}",
                        idempotency_key=f"memory-usage-{index}",
                    )
                    runs.append(
                        repository.complete_run(
                            run["id"],
                            {"finalAnswer": f"answer-{index}", "toolCalls": []},
                        )
                    )

            valid_response = {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": json.dumps({"facts": ["Remember usage attribution."]}),
                            }
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 20,
                        "completion_tokens": 5,
                        "total_tokens": 25,
                        "cost": "0.000125",
                    },
                }
            client = _ScriptedChatClient(
                [
                    {
                        **valid_response,
                        "choices": [{"message": {"role": "assistant", "content": "not-json"}}],
                    },
                    valid_response,
                    valid_response,
                ]
            )
            resolver = MemoryScopeResolver(memory_root)
            try:
                memory_scope = resolver.resolve(
                    trusted_user_id="alice",
                    trusted_workspace_id="workspace-a",
                )
                store = MarkdownMemoryStore(resolver)
                coordinator = MemoryExtractionCoordinator(
                    repository_factory=repository_factory,
                    store=store,
                    scope=memory_scope,
                    extractor=ModelMemoryExtractor(
                        LivePlannerConfig(
                            base_url="mock://memory-usage",
                            model="qwen/memory-usage",
                            api_key="test-only",
                        ),
                        client=client,
                    ),
                    today=lambda: date(2026, 7, 11),
                )
                malformed = coordinator.process_one()
                with patch.object(store, "replace_planned", side_effect=OSError("write failed")):
                    failed_write = coordinator.process_one()
                result = coordinator.process_one()
            finally:
                resolver.close()

            with repository_factory() as repository:
                rows = repository.list_model_usage_calls()
                aggregate = repository.summarize_model_usage()

        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(malformed.status, "FAILED")
        self.assertEqual(failed_write.status, "FAILED")
        self.assertEqual(len(rows), 3)
        self.assertEqual(len({row["call_id"] for row in rows}), 3)
        for row in rows:
            self.assertEqual(row["session_id"], assistant_session["id"])
            self.assertEqual(row["run_id"], runs[-1]["id"])
            self.assertEqual(row["call_kind"], "memory_extractor")
            self.assertEqual(row["model"], "qwen/memory-usage")
            self.assertEqual(row["total_tokens"], 25)
            self.assertEqual(str(row["provider_cost_usd"]), "0.0001250000")
        self.assertEqual(aggregate["total_tokens"], 75)
        self.assertEqual(str(aggregate["known_cost_usd"]), "0.0003750000")
        self.assertEqual(aggregate["session_count"], 1)
        self.assertEqual(aggregate["call_count"], 3)

    def test_pending_call_finalizes_once_and_remains_scoped_and_idempotent(self) -> None:
        from app.modules.ai_assistant.domain.access_scope import AiAssistantAccessScope
        from app.modules.ai_assistant.domain.model_usage import normalize_model_usage
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository, IdempotencyConflict
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        with Mysql8TestDatabase("ai_assistant_model_usage_repository") as database:
            database.create_all(tables=ai_assistant_tables(), register=register_ai_assistant_tables)
            with database.session() as session:
                alice = AiAssistantRepository(
                    session,
                    access_scope=AiAssistantAccessScope("alice", "workspace-a"),
                )
                assistant_session = alice.create_session(title="usage")
                run = alice.create_run(
                    session_id=assistant_session["id"],
                    user_message="measure this call",
                    idempotency_key="usage-call",
                )
                pending = alice.begin_model_usage_call(
                    session_id=assistant_session["id"],
                    run_id=run["id"],
                    call_id="planner:1",
                    call_kind="planner",
                    provider="openrouter",
                    model="qwen/test",
                    started_at=datetime(2026, 7, 11, 10, 0, 0),
                )

                self.assertEqual(pending["usage_source"], "pending")
                self.assertIsNone(pending["input_tokens"])
                self.assertIsNone(pending["cache_write_tokens"])

                recorded = alice.finalize_model_usage_call(
                    run_id=run["id"],
                    call_id="planner:1",
                    usage=normalize_model_usage(
                        {
                            "prompt_tokens": 11,
                            "completion_tokens": 4,
                            "total_tokens": 15,
                            "prompt_tokens_details": {"cached_tokens": 5},
                        }
                    ),
                    completed_at=datetime(2026, 7, 11, 10, 0, 1),
                )
                replayed = alice.finalize_model_usage_call(
                    run_id=run["id"],
                    call_id="planner:1",
                    usage=normalize_model_usage(
                        {"prompt_tokens": 999, "completion_tokens": 1, "total_tokens": 1000}
                    ),
                    completed_at=datetime(2026, 7, 11, 10, 0, 2),
                )

                self.assertEqual(recorded["input_tokens"], 11)
                self.assertEqual(recorded["cache_read_tokens"], 5)
                self.assertIsNone(recorded["cache_write_tokens"])
                self.assertEqual(recorded["total_tokens"], 15)
                self.assertEqual(replayed["input_tokens"], 11)
                with self.assertRaisesRegex(IdempotencyConflict, "identity changed"):
                    alice.begin_model_usage_call(
                        session_id=assistant_session["id"],
                        run_id=run["id"],
                        call_id="planner:1",
                        call_kind="planner",
                        provider="openrouter",
                        model="different/model",
                    )
                failed_run = alice.complete_run(
                    run["id"],
                    {"finalAnswer": "later tool failure"},
                    status="FAILED",
                )
                self.assertEqual(failed_run["status"], "FAILED")
                self.assertEqual(len(alice.list_model_usage_calls()), 1)

                bob = AiAssistantRepository(
                    session,
                    access_scope=AiAssistantAccessScope("bob", "workspace-a"),
                )
                self.assertEqual(bob.list_model_usage_calls(), [])

    def test_call_rejects_session_or_run_from_another_scope(self) -> None:
        from app.modules.ai_assistant.domain.access_scope import AiAssistantAccessScope
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        with Mysql8TestDatabase("ai_assistant_model_usage_scope") as database:
            database.create_all(tables=ai_assistant_tables(), register=register_ai_assistant_tables)
            with database.session() as session:
                alice = AiAssistantRepository(
                    session,
                    access_scope=AiAssistantAccessScope("alice", "workspace-a"),
                )
                assistant_session = alice.create_session(title="alice")
                run = alice.create_run(
                    session_id=assistant_session["id"],
                    user_message="alice",
                    idempotency_key="alice-run",
                )
                bob = AiAssistantRepository(
                    session,
                    access_scope=AiAssistantAccessScope("bob", "workspace-a"),
                )

                with self.assertRaisesRegex(KeyError, "scope"):
                    bob.begin_model_usage_call(
                        session_id=assistant_session["id"],
                        run_id=run["id"],
                        call_id="foreign",
                        call_kind="planner",
                        provider="openrouter",
                        model="qwen/test",
                    )


if __name__ == "__main__":
    unittest.main()


class _ScriptedChatClient:
    def __init__(self, responses: list[dict]) -> None:
        self._responses = responses

    def complete(self, payload: dict) -> dict:
        return self._responses.pop(0)
