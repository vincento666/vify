import json
import os
import tempfile
import unittest
from collections.abc import Generator
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
from app.modules.ai_assistant.infra.repository import AiAssistantRepository
from tests.support.mysql import mysql8_unittest_database


class AiAssistantSessionRuntimeApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_session_runtime_contract",
            tables=ai_assistant_tables(),
            register=register_ai_assistant_tables,
        )
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        self._workspace_dir = tempfile.TemporaryDirectory()
        self._previous_workspace_root = os.environ.get("HIFY_WORKSPACE_ROOT")
        os.environ["HIFY_WORKSPACE_ROOT"] = self._workspace_dir.name
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)

    def tearDown(self) -> None:
        if self._previous_workspace_root is None:
            os.environ.pop("HIFY_WORKSPACE_ROOT", None)
        else:
            os.environ["HIFY_WORKSPACE_ROOT"] = self._previous_workspace_root
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._workspace_dir.cleanup()

    def test_async_message_queues_run_and_worker_completes_from_sse_reconnect(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Session runtime"}).json()[
                "data"
            ]["id"]
            started = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json={
                    "message": "hello async",
                    "idempotencyKey": "session-runtime-async",
                    "approvalMode": "smart_approval",
                    "toolName": "echo_context",
                },
            )
            payload = started.json()["data"]
            run_id = payload["runId"]
            queued_snapshot = client.get(f"/api/v1/ai-assistant/runs/{run_id}/snapshot").json()["data"]
            self._process_run(run_id)
            with client.stream("GET", f"{payload['eventStreamRef']}&_testLimit=40") as stream:
                frames = _read_sse_frames(stream, 40)
            completed_snapshot = client.get(f"/api/v1/ai-assistant/runs/{run_id}/snapshot").json()["data"]

        self.assertEqual(started.status_code, 200, started.text)
        self.assertEqual(payload["status"], "QUEUED")
        self.assertIn("/events/stream?afterSequence=0", payload["eventStreamRef"])
        self.assertEqual(queued_snapshot["run"]["status"], "QUEUED")
        self.assertEqual(queued_snapshot["checkpoint"]["phase"], "queued")
        event_types = [frame["data"]["type"] for frame in frames if frame["event"] == "ai_assistant_event"]
        self.assertIn("run.queued", event_types)
        self.assertIn("run.worker_started", event_types)
        self.assertIn("run.worker_heartbeat", event_types)
        self.assertIn("run.checkpoint_saved", event_types)
        self.assertEqual(completed_snapshot["run"]["status"], "COMPLETED")
        self.assertEqual(completed_snapshot["checkpoint"]["status"], "COMPLETED")

    def test_worker_process_api_executes_queued_run_without_stream_endpoint(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Worker API"}).json()["data"][
                "id"
            ]
            started = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json={
                    "message": "worker api",
                    "idempotencyKey": "session-runtime-worker-api",
                    "approvalMode": "smart_approval",
                    "toolName": "echo_context",
                },
            ).json()["data"]
            processed = client.post(f"/api/v1/ai-assistant/runs/{started['runId']}/worker/process")
            snapshot = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/snapshot").json()["data"]

        self.assertEqual(processed.status_code, 200, processed.text)
        self.assertEqual(processed.json()["data"]["status"], "COMPLETED")
        self.assertEqual(snapshot["run"]["status"], "COMPLETED")
        self.assertEqual(snapshot["checkpoint"]["worker"]["scope"], "durable-lease")

    def test_pause_resume_and_cancel_controls_are_persisted(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Controls"}).json()["data"]["id"]
            first = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json={"message": "pause me", "idempotencyKey": "session-runtime-pause"},
            ).json()["data"]
            paused = client.post(f"/api/v1/ai-assistant/runs/{first['runId']}/pause", json={"actorId": "operator"})
            paused_snapshot = client.get(f"/api/v1/ai-assistant/runs/{first['runId']}/snapshot").json()["data"]
            resumed = client.post(f"/api/v1/ai-assistant/runs/{first['runId']}/resume", json={"actorId": "operator"})
            self._process_run(first["runId"])
            with client.stream("GET", f"{first['eventStreamRef']}&_testLimit=20") as stream:
                _read_sse_frames(stream, 20)
            second = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json={"message": "cancel me", "idempotencyKey": "session-runtime-cancel"},
            ).json()["data"]
            cancelled = client.post(f"/api/v1/ai-assistant/runs/{second['runId']}/cancel", json={"actorId": "operator"})
            cancelled_snapshot = client.get(f"/api/v1/ai-assistant/runs/{second['runId']}/snapshot").json()["data"]

        self.assertEqual(paused.status_code, 200, paused.text)
        self.assertEqual(paused.json()["data"]["status"], "PAUSED")
        self.assertEqual(paused_snapshot["checkpoint"]["status"], "PAUSED")
        self.assertEqual(resumed.status_code, 200, resumed.text)
        self.assertEqual(resumed.json()["data"]["status"], "QUEUED")
        self.assertEqual(cancelled.status_code, 200, cancelled.text)
        self.assertEqual(cancelled.json()["data"]["status"], "CANCELLED")
        self.assertEqual(cancelled_snapshot["checkpoint"]["status"], "CANCELLED")
        self.assertEqual(cancelled_snapshot["run"]["status"], "CANCELLED")

    def test_pending_approval_recovers_from_snapshot_after_async_worker_runs(self) -> None:
        Path(self._workspace_dir.name, "needs-approval.txt").write_text("old\n", encoding="utf-8")

        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Approval recovery"}).json()[
                "data"
            ]["id"]
            started = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json={
                    "message": "write pending approval",
                    "idempotencyKey": "session-runtime-approval",
                    "approvalMode": "smart_approval",
                    "toolName": "write_workspace_file",
                    "toolInput": {"path": "needs-approval.txt", "content": "new\n"},
                },
            ).json()["data"]
            self._process_run(started["runId"])
            with client.stream("GET", f"{started['eventStreamRef']}&_testLimit=12") as stream:
                _read_sse_frames(stream, 12)
            snapshot = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/snapshot").json()["data"]

        self.assertEqual(snapshot["run"]["status"], "WAITING_APPROVAL")
        self.assertEqual(snapshot["checkpoint"]["status"], "WAITING_APPROVAL")
        self.assertEqual(snapshot["inspector"]["approvalQueue"][0]["toolName"], "write_workspace_file")
        self.assertEqual(snapshot["inspector"]["plan"]["status"], "BLOCKED")

    def test_cancelled_waiting_approval_cannot_be_approved_later(self) -> None:
        target = Path(self._workspace_dir.name, "cancelled-approval.txt")
        target.write_text("old\n", encoding="utf-8")

        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Cancel approval"}).json()[
                "data"
            ]["id"]
            started = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json={
                    "message": "write then cancel",
                    "idempotencyKey": "session-runtime-cancel-approval",
                    "approvalMode": "smart_approval",
                    "toolName": "write_workspace_file",
                    "toolInput": {"path": "cancelled-approval.txt", "content": "new\n"},
                },
            ).json()["data"]
            self._process_run(started["runId"])
            with client.stream("GET", f"{started['eventStreamRef']}&_testLimit=12") as stream:
                _read_sse_frames(stream, 12)
            approval_id = client.get("/api/v1/ai-assistant/approvals").json()["data"]["list"][0]["id"]
            cancelled = client.post(f"/api/v1/ai-assistant/runs/{started['runId']}/cancel", json={"actorId": "operator"})
            stale_approve = client.post(
                f"/api/v1/ai-assistant/approvals/{approval_id}/approve",
                json={"actorId": "operator"},
            )
            snapshot = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/snapshot").json()["data"]

        self.assertEqual(cancelled.status_code, 200, cancelled.text)
        self.assertEqual(cancelled.json()["data"]["status"], "CANCELLED")
        self.assertIn(stale_approve.status_code, {400, 409})
        self.assertEqual(target.read_text(encoding="utf-8"), "old\n")
        self.assertEqual(snapshot["run"]["status"], "CANCELLED")
        self.assertEqual(snapshot["inspector"]["approvalQueue"], [])

    def test_terminal_run_control_is_rejected_without_misleading_event(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Terminal control"}).json()[
                "data"
            ]["id"]
            completed = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={"message": "complete me", "idempotencyKey": "session-runtime-terminal-control"},
            ).json()["data"]
            rejected = client.post(f"/api/v1/ai-assistant/runs/{completed['runId']}/cancel", json={"actorId": "operator"})
            events = client.get(f"/api/v1/ai-assistant/runs/{completed['runId']}/events").json()["data"]["list"]

        self.assertIn(rejected.status_code, {400, 409})
        self.assertNotIn("run.cancelled", [event["type"] for event in events])

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
