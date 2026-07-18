import json
import os
import tempfile
import unittest
from collections.abc import Generator
from pathlib import Path
from time import monotonic, sleep

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from app.modules.ai_assistant.runtime_job_worker import AI_ASSISTANT_RUNTIME_JOB_TYPE
from app.modules.runtime.composition import build_runtime_job_worker
from app.modules.runtime.infra.runtime_job_repository import RuntimeJobRepository
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
        app.dependency_overrides[get_settings] = lambda: Settings(
            _env_file=None,
            ai_assistant_tool_profile="demo",
        )

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

    def test_worker_process_api_only_enqueues_and_inspects_for_compatibility(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Worker API shim"}).json()[
                "data"
            ]["id"]
            started = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json={
                    "message": "worker api compatibility shim",
                    "idempotencyKey": "session-runtime-worker-api",
                    "approvalMode": "smart_approval",
                    "toolName": "echo_context",
                },
            ).json()["data"]
            processed = client.post(f"/api/v1/ai-assistant/runs/{started['runId']}/worker/process")
            snapshot = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/snapshot").json()["data"]
            job_status = self._runtime_job_status(started["runId"])

        self.assertEqual(processed.status_code, 200, processed.text)
        self.assertEqual(processed.json()["data"]["status"], "QUEUED")
        self.assertEqual(snapshot["run"]["status"], "QUEUED")
        self.assertEqual(job_status, "QUEUED")
        self.assertEqual(
            processed.json()["data"]["deprecation"],
            {
                "deprecated": True,
                "replacement": "standalone-runtime-worker",
                "requestPayloadIgnored": False,
                "sunsetAt": "2026-08-01",
                "removalGate": "external-consumer-inventory",
            },
        )

    def test_async_message_is_completed_by_standalone_worker_without_compat_api(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Standalone worker"}).json()[
                "data"
            ]["id"]
            started = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json={
                    "message": "backend closes the loop",
                    "idempotencyKey": "session-runtime-autonomous-worker",
                    "approvalMode": "smart_approval",
                    "toolName": "echo_context",
                },
            )
            run_id = started.json()["data"]["runId"]
            worker_result = self._process_run(run_id)
            snapshot = _wait_for_run_status(client, run_id, {"COMPLETED"})
            _wait_for_event_type(client, run_id, "run.worker_heartbeat")
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events").json()["data"]["list"]

        self.assertEqual(started.status_code, 200, started.text)
        self.assertEqual(started.json()["data"]["status"], "QUEUED")
        self.assertEqual(worker_result["status"], "COMPLETED")
        self.assertEqual(snapshot["run"]["status"], "COMPLETED")
        event_types = [event["type"] for event in events]
        self.assertIn("run.queued", event_types)
        self.assertIn("run.worker_started", event_types)
        self.assertIn("run.worker_heartbeat", event_types)
        self.assertIn("run.checkpoint_saved", event_types)

    def test_repeated_compat_inspection_does_not_duplicate_standalone_worker_claim(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Duplicate claim"}).json()[
                "data"
            ]["id"]
            started = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json={
                    "message": "manual worker races auto worker",
                    "idempotencyKey": "session-runtime-duplicate-worker-claim",
                    "approvalMode": "smart_approval",
                    "toolName": "echo_context",
                },
            ).json()["data"]
            first_compat = client.post(f"/api/v1/ai-assistant/runs/{started['runId']}/worker/process")
            second_compat = client.post(f"/api/v1/ai-assistant/runs/{started['runId']}/worker/process")
            completed = self._process_run(started["runId"])
            retry = self._process_run(started["runId"])
            _wait_for_event_type(client, started["runId"], "run.worker_heartbeat")
            sleep(0.1)
            events = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/events").json()["data"]["list"]
            snapshot = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/snapshot").json()["data"]

        self.assertEqual(first_compat.status_code, 200, first_compat.text)
        self.assertEqual(second_compat.status_code, 200, second_compat.text)
        self.assertEqual(first_compat.json()["data"]["status"], "QUEUED")
        self.assertEqual(second_compat.json()["data"]["status"], "QUEUED")
        self.assertEqual(completed["status"], "COMPLETED")
        self.assertEqual(retry["status"], "IDLE")
        self.assertEqual(snapshot["run"]["status"], "COMPLETED")
        event_types = [event["type"] for event in events]
        self.assertEqual(event_types.count("run.worker_started"), 1)
        self.assertEqual(event_types.count("run.worker_heartbeat"), 1)
        self.assertEqual(event_types.count("run.completed"), 1)

    def test_pause_resume_and_cancel_controls_are_persisted(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Controls"}).json()["data"]["id"]
            first = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json={"message": "pause me", "idempotencyKey": "session-runtime-pause"},
            ).json()["data"]
            paused = client.post(f"/api/v1/ai-assistant/runs/{first['runId']}/pause", json={"actorId": "operator"})
            paused_snapshot = client.get(f"/api/v1/ai-assistant/runs/{first['runId']}/snapshot").json()["data"]
            paused_job_status = self._runtime_job_status(first["runId"])
            resumed = client.post(f"/api/v1/ai-assistant/runs/{first['runId']}/resume", json={"actorId": "operator"})
            resumed_job_status = self._runtime_job_status(first["runId"])
            self._process_run(first["runId"])
            _wait_for_run_status(client, first["runId"], {"COMPLETED"})
            with client.stream("GET", f"{first['eventStreamRef']}&_testLimit=20") as stream:
                _read_sse_frames(stream, 20)
            second = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json={"message": "cancel me", "idempotencyKey": "session-runtime-cancel"},
            ).json()["data"]
            cancelled = client.post(f"/api/v1/ai-assistant/runs/{second['runId']}/cancel", json={"actorId": "operator"})
            cancelled_snapshot = client.get(f"/api/v1/ai-assistant/runs/{second['runId']}/snapshot").json()["data"]
            cancelled_job_status = self._runtime_job_status(second["runId"])

        self.assertEqual(paused.status_code, 200, paused.text)
        self.assertEqual(paused.json()["data"]["status"], "PAUSED")
        self.assertEqual(paused_snapshot["checkpoint"]["status"], "PAUSED")
        self.assertEqual(
            paused_snapshot["checkpoint"]["control"]["actorId"],
            "local-user",
        )
        self.assertEqual(resumed.status_code, 200, resumed.text)
        self.assertEqual(resumed.json()["data"]["status"], "QUEUED")
        self.assertEqual(paused_job_status, "CANCELLED")
        self.assertEqual(resumed_job_status, "QUEUED")
        self.assertEqual(cancelled.status_code, 200, cancelled.text)
        self.assertEqual(cancelled.json()["data"]["status"], "CANCELLED")
        self.assertEqual(cancelled_snapshot["checkpoint"]["status"], "CANCELLED")
        self.assertEqual(cancelled_snapshot["run"]["status"], "CANCELLED")
        self.assertEqual(cancelled_job_status, "CANCELLED")

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

    def _process_run(self, run_id: int) -> dict:
        with self._factory() as session:
            job = RuntimeJobRepository(session).get_by_run(
                run_id,
                owner_type="AI_ASSISTANT",
                job_type=AI_ASSISTANT_RUNTIME_JOB_TYPE,
            )
            self.assertIsNotNone(job)
            return build_runtime_job_worker(
                session,
                owner="ai-assistant",
                worker_id=f"contract-worker-{run_id}",
                settings=Settings(
                    _env_file=None,
                    ai_assistant_tool_profile="demo",
                ),
            ).run_once(job_id=int(job["id"]))

    def _runtime_job_status(self, run_id: int) -> str:
        with self._factory() as session:
            job = RuntimeJobRepository(session).get_by_run(
                run_id,
                owner_type="AI_ASSISTANT",
                job_type=AI_ASSISTANT_RUNTIME_JOB_TYPE,
            )
            self.assertIsNotNone(job)
            return str(job["status"])


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


def _wait_for_run_status(client: TestClient, run_id: int, expected_statuses: set[str]) -> dict:
    last: dict | None = None
    deadline = monotonic() + 5
    while monotonic() < deadline:
        last = client.get(f"/api/v1/ai-assistant/runs/{run_id}/snapshot").json()["data"]
        if last["run"]["status"] in expected_statuses:
            return last
        sleep(0.025)
    raise AssertionError(f"run {run_id} did not reach {expected_statuses}; last={last}")


def _wait_for_event_type(client: TestClient, run_id: int, event_type: str) -> list[dict]:
    last: list[dict] = []
    deadline = monotonic() + 5
    while monotonic() < deadline:
        last = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events").json()["data"]["list"]
        if event_type in {event["type"] for event in last}:
            return last
        sleep(0.025)
    raise AssertionError(f"run {run_id} did not emit {event_type}; last={last}")


if __name__ == "__main__":
    unittest.main()
