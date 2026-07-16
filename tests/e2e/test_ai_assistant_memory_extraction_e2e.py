import json
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


class AiAssistantMemoryExtractionE2ETest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_memory_extraction_e2e",
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
        app.state.ai_assistant_memory_extractor = _Extractor()
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

    def test_extracted_memory_survives_client_reload_and_cursor_stores_no_text(self) -> None:
        headers = {"X-Hify-Actor-Id": "alice"}
        with TestClient(app) as client:
            session_id = client.post(
                "/api/v1/ai-assistant/sessions",
                headers=headers,
                json={"title": "extract"},
            ).json()["data"]["id"]
            runs = [
                self._run(client, headers, session_id, index)
                for index in range(3)
            ]
            snapshots = []
            for _ in range(150):
                snapshots = [
                    client.get(
                        f"/api/v1/ai-assistant/runs/{run['runId']}/inspector",
                        headers=headers,
                    ).json()["data"]
                    for run in runs
                ]
                if all(snapshot["run"]["status"] == "COMPLETED" for snapshot in snapshots) and snapshots[
                    -1
                ]["memory"]["workingMemory"]:
                    break
                time.sleep(0.02)

        with TestClient(app) as reloaded:
            later_session = reloaded.post(
                "/api/v1/ai-assistant/sessions",
                headers=headers,
                json={"title": "later"},
            ).json()["data"]["id"]
            later = reloaded.post(
                f"/api/v1/ai-assistant/sessions/{later_session}/messages",
                headers=headers,
                json={"message": "use memory", "idempotencyKey": "e2e-later"},
            ).json()["data"]
            memory = reloaded.get(
                f"/api/v1/ai-assistant/runs/{later['runId']}/inspector",
                headers=headers,
            ).json()["data"]["memory"]

        self.assertTrue(all(snapshot["run"]["status"] == "COMPLETED" for snapshot in snapshots))
        self.assertIn("Remember extracted E2E fact.", memory["workingMemory"][0]["value"])
        with self._factory() as session:
            from app.modules.ai_assistant.domain.access_scope import access_scope_for_workspace
            from app.modules.ai_assistant.infra.repository import AiAssistantRepository

            repository = AiAssistantRepository(
                session,
                access_scope=access_scope_for_workspace(
                    trusted_user_id="alice",
                    trusted_workspace_root=self._workspace.name,
                ),
            )
            cursor = repository.get_memory_extraction_cursor()
        serialized = json.dumps(cursor, ensure_ascii=False, default=str)
        self.assertNotIn("Remember extracted E2E fact.", serialized)
        self.assertEqual(cursor["last_processed_run_id"], runs[-1]["runId"])

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session

    @staticmethod
    def _run(
        client: TestClient,
        headers: dict[str, str],
        session_id: int,
        index: int,
    ) -> dict:
        started = client.post(
            f"/api/v1/ai-assistant/sessions/{session_id}/messages",
            headers=headers,
            json={"message": f"turn-{index}", "idempotencyKey": f"e2e-{index}"},
        ).json()["data"]
        processed = client.post(
            f"/api/v1/ai-assistant/runs/{started['runId']}/worker/process",
            headers=headers,
        ).json()["data"]
        return {**processed, "runId": processed["id"]}


class _Extractor:
    def extract(self, runs: list[dict]) -> list[str]:
        return ["Remember extracted E2E fact."]


if __name__ == "__main__":
    unittest.main()
