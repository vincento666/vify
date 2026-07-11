import os
import tempfile
import time
import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from tests.support.mysql import mysql8_unittest_database


class AiAssistantMemoryExtractionApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_memory_extraction_api",
            tables=ai_assistant_tables(),
            register=register_ai_assistant_tables,
        )
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        self._workspace = tempfile.TemporaryDirectory()
        self._memory = tempfile.TemporaryDirectory()
        self._previous_workspace = os.environ.get("HIFY_WORKSPACE_ROOT")
        self._previous_memory = os.environ.get("HIFY_AI_ASSISTANT_MEMORY_ROOT")
        self._previous_extractor = getattr(app.state, "ai_assistant_memory_extractor", None)
        self._previous_autonomous_worker = getattr(
            app.state,
            "ai_assistant_autonomous_worker_enabled",
            None,
        )
        os.environ["HIFY_WORKSPACE_ROOT"] = self._workspace.name
        os.environ["HIFY_AI_ASSISTANT_MEMORY_ROOT"] = self._memory.name
        self.extractor = _FakeExtractor()
        app.state.ai_assistant_memory_extractor = self.extractor
        app.state.ai_assistant_autonomous_worker_enabled = False
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)

    def tearDown(self) -> None:
        if self._previous_workspace is None:
            os.environ.pop("HIFY_WORKSPACE_ROOT", None)
        else:
            os.environ["HIFY_WORKSPACE_ROOT"] = self._previous_workspace
        if self._previous_memory is None:
            os.environ.pop("HIFY_AI_ASSISTANT_MEMORY_ROOT", None)
        else:
            os.environ["HIFY_AI_ASSISTANT_MEMORY_ROOT"] = self._previous_memory
        if self._previous_extractor is None:
            app.state.__dict__["_state"].pop("ai_assistant_memory_extractor", None)
        else:
            app.state.ai_assistant_memory_extractor = self._previous_extractor
        if self._previous_autonomous_worker is None:
            app.state.__dict__["_state"].pop("ai_assistant_autonomous_worker_enabled", None)
        else:
            app.state.ai_assistant_autonomous_worker_enabled = self._previous_autonomous_worker
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._workspace.cleanup()
        self._memory.cleanup()

    def test_third_completed_run_across_sessions_updates_memory_once(self) -> None:
        headers = {"X-Hify-Actor-Id": "alice"}
        with TestClient(app) as client:
            first_session = client.post(
                "/api/v1/ai-assistant/sessions",
                headers=headers,
                json={"title": "first"},
            ).json()["data"]["id"]
            second_session = client.post(
                "/api/v1/ai-assistant/sessions",
                headers=headers,
                json={"title": "second"},
            ).json()["data"]["id"]
            first = self._run(client, headers, first_session, "first")
            replayed_first = self._run(client, headers, first_session, "first")
            second = self._run(client, headers, second_session, "second")
            before = client.get(
                f"/api/v1/ai-assistant/runs/{second['runId']}/inspector",
                headers=headers,
            ).json()["data"]["memory"]
            third = self._run(client, headers, first_session, "third")

            projected = ""
            for _ in range(150):
                memory = client.get(
                    f"/api/v1/ai-assistant/runs/{third['runId']}/inspector",
                    headers=headers,
                ).json()["data"]["memory"]
                if memory["workingMemory"]:
                    projected = memory["workingMemory"][0]["value"]
                    break
                time.sleep(0.02)
            fourth = self._run(client, headers, second_session, "fourth")
            fifth = self._run(client, headers, first_session, "fifth")
            sixth = self._run(client, headers, second_session, "sixth")
            self._wait_for_memory_worker(status="IDLE", last_run_id=sixth["runId"])

        self.assertEqual(first["status"], "COMPLETED")
        self.assertTrue(replayed_first["replayed"])
        self.assertEqual(second["status"], "COMPLETED")
        self.assertEqual(third["status"], "COMPLETED")
        self.assertEqual(fourth["status"], "COMPLETED")
        self.assertEqual(fifth["status"], "COMPLETED")
        self.assertEqual(sixth["status"], "COMPLETED")
        self.assertEqual(before["workingMemory"], [])
        self.assertIn("Remember API cadence across sessions.", projected)
        self.assertEqual(self.extractor.calls, 2)
        self.assertEqual(len(self.extractor.last_run_ids), 3)

    def test_plan_only_and_approval_completion_both_trigger_third_run_extraction(self) -> None:
        headers = {"X-Hify-Actor-Id": "alice"}
        with TestClient(app) as client:
            session_id = client.post(
                "/api/v1/ai-assistant/sessions",
                headers=headers,
                json={"title": "all completion paths"},
            ).json()["data"]["id"]
            plan_only = self._run(
                client,
                headers,
                session_id,
                "plan-only",
                planningStrategy="plan_only",
            )
            ordinary = self._run(client, headers, session_id, "ordinary")
            waiting = self._run(
                client,
                headers,
                session_id,
                "approval",
                approvalMode="ask_each_time",
                toolName="write_workspace_file",
                toolInput={"path": "approval-memory.txt", "content": "approved"},
            )
            approval_id = client.get(
                "/api/v1/ai-assistant/approvals",
                headers=headers,
            ).json()["data"]["list"][0]["id"]
            approved = client.post(
                f"/api/v1/ai-assistant/approvals/{approval_id}/approve",
                headers=headers,
                json={"actorId": "operator-memory"},
            ).json()["data"]
            self._wait_for_memory_worker(status="IDLE", last_run_id=waiting["runId"])

        self.assertEqual(plan_only["status"], "COMPLETED")
        self.assertEqual(ordinary["status"], "COMPLETED")
        self.assertEqual(waiting["status"], "WAITING_APPROVAL")
        self.assertEqual(approved["status"], "APPROVED")
        self.assertEqual(self.extractor.calls, 1)

    def test_extraction_failure_keeps_runs_completed_and_retries_same_batch(self) -> None:
        failing = _FailingExtractor()
        app.state.ai_assistant_memory_extractor = failing
        headers = {"X-Hify-Actor-Id": "alice"}
        with TestClient(app) as client:
            session_id = client.post(
                "/api/v1/ai-assistant/sessions",
                headers=headers,
                json={"title": "retry"},
            ).json()["data"]["id"]
            completed = [
                self._run(client, headers, session_id, f"retry-{index}")
                for index in range(3)
            ]
            self._wait_for_memory_worker(status="FAILED")
            failure_events = client.get(
                f"/api/v1/ai-assistant/runs/{completed[-1]['runId']}/events",
                headers=headers,
            ).json()["data"]["list"]

            retry = _FakeExtractor()
            app.state.ai_assistant_memory_extractor = retry
            trigger = self._run(client, headers, session_id, "retry-trigger")
            trigger_events = client.get(
                f"/api/v1/ai-assistant/runs/{trigger['runId']}/events",
                headers=headers,
            ).json()["data"]["list"]
            projected = ""
            for _ in range(150):
                memory = client.get(
                    f"/api/v1/ai-assistant/runs/{trigger['runId']}/inspector",
                    headers=headers,
                ).json()["data"]["memory"]
                if memory["workingMemory"]:
                    projected = memory["workingMemory"][0]["value"]
                    break
                time.sleep(0.02)
            self._wait_for_memory_worker(
                status="IDLE",
                last_run_id=completed[-1]["runId"],
            )

        self.assertTrue(all(run["status"] == "COMPLETED" for run in completed))
        self.assertEqual(trigger["status"], "COMPLETED", trigger_events)
        self.assertEqual(failing.calls, 1)
        self.assertIn("memory.extraction_failed", [event["type"] for event in failure_events])
        self.assertEqual(retry.calls, 1)
        self.assertEqual(retry.last_run_ids, [run["runId"] for run in completed])
        self.assertIn("Remember API cadence across sessions.", projected)

    @staticmethod
    def _run(
        client: TestClient,
        headers: dict[str, str],
        session_id: int,
        message: str,
        **overrides: object,
    ) -> dict:
        payload = {"message": message, "idempotencyKey": f"extract-{message}", **overrides}
        started = client.post(
            f"/api/v1/ai-assistant/sessions/{session_id}/messages",
            headers=headers,
            json=payload,
        ).json()["data"]
        if started["status"] not in {"RUNNING", "QUEUED"}:
            return started
        processed = client.post(
            f"/api/v1/ai-assistant/runs/{started['runId']}/worker/process",
            headers=headers,
        ).json()["data"]
        return {**processed, "runId": processed["id"]}

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session

    def _wait_for_memory_worker(
        self,
        *,
        status: str,
        last_run_id: int | None = None,
    ) -> None:
        from app.modules.ai_assistant.domain.access_scope import access_scope_for_workspace
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository
        from app.modules.ai_assistant.web import router

        access_scope = access_scope_for_workspace(
            trusted_user_id="alice",
            trusted_workspace_root=self._workspace.name,
        )
        scope_key = f"{access_scope.user_id}\0{access_scope.workspace_id}"
        for _ in range(250):
            with self._factory() as session:
                cursor = AiAssistantRepository(
                    session,
                    access_scope=access_scope,
                ).get_memory_extraction_cursor()
            with router._MEMORY_EXTRACTION_LOCK:
                in_flight = scope_key in router._MEMORY_EXTRACTION_IN_FLIGHT
            cursor_matches = cursor is not None and cursor["status"] == status
            if last_run_id is not None:
                cursor_matches = cursor_matches and cursor["last_processed_run_id"] == last_run_id
            if cursor_matches and not in_flight:
                return
            time.sleep(0.02)
        self.fail(f"memory worker did not settle: status={status}, last_run_id={last_run_id}")


class _FakeExtractor:
    def __init__(self) -> None:
        self.calls = 0
        self.last_run_ids: list[int] = []

    def extract(self, runs: list[dict]) -> list[str]:
        self.calls += 1
        self.last_run_ids = [int(run["id"]) for run in runs]
        return ["Remember API cadence across sessions."]


class _FailingExtractor:
    def __init__(self) -> None:
        self.calls = 0

    def extract(self, runs: list[dict]) -> list[str]:
        self.calls += 1
        raise RuntimeError("fake extraction failure")


if __name__ == "__main__":
    unittest.main()
