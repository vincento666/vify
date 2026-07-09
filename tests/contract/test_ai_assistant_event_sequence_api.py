from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import threading
import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from app.modules.ai_assistant.infra.repository import AiAssistantRepository
from tests.support.mysql import mysql8_unittest_database


class AiAssistantEventSequenceApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_event_sequence_contract",
            tables=ai_assistant_tables(),
            register=register_ai_assistant_tables,
        )
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_events_api_replays_gapless_sequence_after_concurrent_append(self) -> None:
        worker_count = 16
        with self._factory() as session:
            repository = AiAssistantRepository(session)
            assistant_session = repository.create_session(title="Concurrent API replay")
            run = repository.create_run(
                session_id=assistant_session["id"],
                user_message="Append concurrently",
                idempotency_key="event-sequence-api-concurrent",
            )
            run_id = int(run["id"])
            session_id = int(assistant_session["id"])

        barrier = threading.Barrier(worker_count)

        def append_event(index: int) -> int:
            barrier.wait(timeout=5)
            with self._factory() as session:
                repository = AiAssistantRepository(session)
                event = repository.append_event(
                    run_id=run_id,
                    session_id=session_id,
                    event_type="tool.call_completed",
                    visible_title=f"Tool completed {index}",
                    visible_summary="Concurrent event append.",
                    payload={"index": index},
                )
                return int(event["sequence"])

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            sequences = list(executor.map(append_event, range(worker_count)))

        with TestClient(app) as client:
            all_events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events")
            replayed = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events", params={"afterSequence": 5})

        expected = list(range(1, worker_count + 1))
        self.assertEqual(sorted(sequences), expected)
        self.assertEqual(all_events.status_code, 200, all_events.text)
        self.assertEqual(replayed.status_code, 200, replayed.text)
        self.assertEqual([event["sequence"] for event in all_events.json()["data"]["list"]], expected)
        self.assertEqual(
            [event["sequence"] for event in replayed.json()["data"]["list"]],
            list(range(6, worker_count + 1)),
        )

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
