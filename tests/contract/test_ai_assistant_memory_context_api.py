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


class AiAssistantMemoryContextApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_memory_context_contract",
            tables=ai_assistant_tables(),
            register=register_ai_assistant_tables,
        )
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        self._workspace_dir = tempfile.TemporaryDirectory()
        self._previous_workspace_root = os.environ.get("HIFY_WORKSPACE_ROOT")
        os.environ["HIFY_WORKSPACE_ROOT"] = self._workspace_dir.name
        Path(self._workspace_dir.name, "AGENTS.md").write_text("Use concise Chinese responses.\n", encoding="utf-8")
        nested = Path(self._workspace_dir.name, "nested", "project")
        nested.mkdir(parents=True)
        Path(self._workspace_dir.name, "nested", "AGENTS.md").write_text(
            "Prefer nested project instructions.\n",
            encoding="utf-8",
        )
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

    def test_run_records_instruction_session_working_memory_and_context_budget(self) -> None:
        with TestClient(app) as client:
            created = client.post(
                "/api/v1/ai-assistant/sessions",
                json={
                    "title": "Memory context",
                    "context": {
                        "aiAssistantWorkspace": {"cwd": "nested/project"},
                        "aiAssistantContextBudget": {"maxContextTokens": 96},
                        "aiAssistantMemory": {
                            "sessionSummary": {
                                "content": "Earlier discussion confirmed the adapter seam stays mock-only.",
                                "sourceMessageIds": [100],
                                "sourceEventIds": [200],
                                "algorithm": "seeded-test",
                                "tokenEstimate": 9,
                                "hash": "seeded",
                            },
                            "workingMemory": [
                                {
                                    "key": "adapter_boundary",
                                    "value": "mock aviation only",
                                    "source": "user-confirmed",
                                    "status": "active",
                                }
                            ],
                        },
                    },
                },
            )
            session_id = created.json()["data"]["id"]
            turn = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={"message": "继续推进 harness", "idempotencyKey": "memory-context-contract"},
            )
            run_id = turn.json()["data"]["runId"]
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events").json()["data"]["list"]
            inspector = client.get(f"/api/v1/ai-assistant/runs/{run_id}/inspector").json()["data"]
            session = client.get(f"/api/v1/ai-assistant/sessions/{session_id}").json()["data"]

        event_types = [event["type"] for event in events]
        self.assertIn("context.budget_estimated", event_types)
        self.assertIn("context.layer_selected", event_types)
        self.assertIn("context.compaction_started", event_types)
        self.assertIn("context.compaction_completed", event_types)
        self.assertIn("context.layer_dropped", event_types)
        context_budget = inspector["contextBudget"]
        self.assertGreater(context_budget["usage"]["usagePercent"], 0)
        self.assertEqual(context_budget["usage"]["maxTokens"], 96)
        self.assertTrue(any(layer["name"] == "AGENTS.md" for layer in context_budget["layers"]))
        instruction_paths = [layer["path"] for layer in inspector["memory"]["instructionMemory"]]
        self.assertEqual(len(instruction_paths), 2)
        self.assertTrue(instruction_paths[0].endswith("AGENTS.md"))
        self.assertTrue(instruction_paths[1].endswith("nested/AGENTS.md"))
        self.assertTrue(any(layer["name"] == "session_summary" for layer in context_budget["layers"]))
        self.assertTrue(any(layer["name"] == "working_memory" for layer in context_budget["layers"]))
        self.assertTrue(context_budget["compactionSnapshot"]["summaryHash"])
        self.assertEqual(inspector["memory"]["workingMemory"][0]["key"], "adapter_boundary")
        self.assertIn("继续推进 harness", inspector["memory"]["sessionSummary"]["content"])
        self.assertEqual(inspector["memory"]["sessionSummary"]["algorithm"], "deterministic-session-summary-v1")
        updated_memory = session["context"]["aiAssistantMemory"]
        self.assertIn("继续推进 harness", updated_memory["sessionSummary"]["content"])
        self.assertTrue(updated_memory["sessionSummary"]["hash"])
        self.assertGreaterEqual(len(updated_memory["sessionSummary"]["sourceMessageIds"]), 1)

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
