import json
import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
from app.modules.ai_assistant.infra.repository import AiAssistantRepository
from tests.support.mysql import mysql8_unittest_database


class AiAssistantSessionRuntimeE2ETest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_session_runtime_e2e",
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

    def test_refresh_snapshot_then_sse_resume_completes_queued_run(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Session E2E"}).json()["data"][
                "id"
            ]
            started = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json={"message": "recover me", "idempotencyKey": "session-runtime-e2e"},
            ).json()["data"]
            queued_snapshot = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/snapshot").json()["data"]
            queued_sequence = queued_snapshot["streamCursor"]["lastSequence"]
            self._process_run(started["runId"])
            with client.stream(
                "GET",
                f"/api/v1/ai-assistant/runs/{started['runId']}/events/stream",
                headers={"Last-Event-ID": str(queued_sequence)},
            ) as stream:
                resumed = _read_sse_frames(stream, 20)
            completed_snapshot = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/snapshot").json()["data"]

        self.assertEqual(queued_snapshot["run"]["status"], "QUEUED")
        self.assertEqual(queued_snapshot["checkpoint"]["phase"], "queued")
        event_types = [frame["data"]["type"] for frame in resumed if frame["event"] == "ai_assistant_event"]
        self.assertIn("run.worker_started", event_types)
        self.assertIn("run.completed", event_types)
        self.assertEqual(completed_snapshot["run"]["status"], "COMPLETED")
        self.assertEqual(completed_snapshot["checkpoint"]["status"], "COMPLETED")

    def test_worker_processes_queued_run_without_stream_and_records_durable_lease(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Worker E2E"}).json()["data"][
                "id"
            ]
            started = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json={"message": "worker claim me", "idempotencyKey": "session-runtime-worker-lease"},
            ).json()["data"]

        with self._factory() as session:
            result = AiAssistantHarnessService(AiAssistantRepository(session)).process_queued_run(started["runId"])
            self.assertIsNotNone(result)

        with TestClient(app) as client:
            snapshot = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/snapshot").json()["data"]
            events = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/events").json()["data"]["list"]

        self.assertEqual(snapshot["run"]["status"], "COMPLETED")
        worker = snapshot["checkpoint"]["worker"]
        self.assertEqual(worker["scope"], "durable-lease")
        self.assertIn("leaseToken", worker)
        self.assertIn("leaseExpiresAt", worker)
        self.assertIn("run.worker_started", [event["type"] for event in events])

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session

    def _process_run(self, run_id: int) -> None:
        with self._factory() as session:
            result = AiAssistantHarnessService(AiAssistantRepository(session)).process_queued_run(run_id)
            self.assertIsNotNone(result)


def _read_sse_frames(response, count: int) -> list[dict]:
    frames: list[dict] = []
    current_event = "message"
    for line in response.iter_lines():
        if not line:
            continue
        if line.startswith("event: "):
            current_event = line.removeprefix("event: ").strip()
            continue
        if line.startswith("data: "):
            frames.append({"event": current_event, "data": json.loads(line.removeprefix("data: "))})
            current_event = "message"
            if len(frames) >= count:
                return frames
    return frames


if __name__ == "__main__":
    unittest.main()
