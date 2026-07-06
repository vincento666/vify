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
from tests.support.mysql import mysql8_unittest_database


class AiAssistantMemoryContextE2ETest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_memory_context_e2e",
            tables=ai_assistant_tables(),
            register=register_ai_assistant_tables,
        )
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        self._workspace_dir = tempfile.TemporaryDirectory()
        self._previous_workspace_root = os.environ.get("HIFY_WORKSPACE_ROOT")
        os.environ["HIFY_WORKSPACE_ROOT"] = self._workspace_dir.name
        Path(self._workspace_dir.name, "AGENTS.md").write_text("Keep context budgets auditable.\n", encoding="utf-8")
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

    def test_async_run_recovers_context_budget_and_memory_from_snapshot(self) -> None:
        with TestClient(app) as client:
            session_id = client.post(
                "/api/v1/ai-assistant/sessions",
                json={
                    "title": "Memory E2E",
                    "context": {
                        "aiAssistantContextBudget": {"maxContextTokens": 128},
                        "aiAssistantMemory": {
                            "workingMemory": [
                                {
                                    "key": "current_slice",
                                    "value": "222.6 MemoryContext",
                                    "source": "user-confirmed",
                                    "status": "active",
                                }
                            ]
                        },
                    },
                },
            ).json()["data"]["id"]
            started = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json={"message": "恢复上下文预算", "idempotencyKey": "memory-context-e2e"},
            ).json()["data"]
            with client.stream("GET", f"{started['eventStreamRef']}&_testLimit=20") as stream:
                _read_sse_frames(stream, 20)
            snapshot = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/snapshot").json()["data"]
            session = client.get(f"/api/v1/ai-assistant/sessions/{session_id}").json()["data"]

        self.assertEqual(snapshot["run"]["status"], "COMPLETED")
        self.assertEqual(snapshot["inspector"]["memory"]["workingMemory"][0]["key"], "current_slice")
        self.assertEqual(snapshot["inspector"]["contextBudget"]["usage"]["maxTokens"], 128)
        self.assertTrue(snapshot["inspector"]["contextBudget"]["selectedLayers"])
        self.assertTrue(session["context"]["aiAssistantMemory"]["sessionSummary"]["hash"])

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session


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
            import json

            frames.append({"event": current_event, "data": json.loads(line.removeprefix("data: "))})
            current_event = "message"
            if len(frames) >= count:
                return frames
    return frames


if __name__ == "__main__":
    unittest.main()
