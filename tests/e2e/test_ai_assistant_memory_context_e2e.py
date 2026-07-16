import os
import tempfile
import time
import unittest
from collections.abc import Generator
from datetime import date, timedelta
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
        self._memory_dir = tempfile.TemporaryDirectory()
        self._previous_workspace_root = os.environ.get("HIFY_WORKSPACE_ROOT")
        self._previous_memory_root = os.environ.get("HIFY_AI_ASSISTANT_MEMORY_ROOT")
        os.environ["HIFY_WORKSPACE_ROOT"] = self._workspace_dir.name
        os.environ["HIFY_AI_ASSISTANT_MEMORY_ROOT"] = self._memory_dir.name
        Path(self._workspace_dir.name, "AGENTS.md").write_text("Keep context budgets auditable.\n", encoding="utf-8")
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)
        self._seed_memory()

    def tearDown(self) -> None:
        if self._previous_workspace_root is None:
            os.environ.pop("HIFY_WORKSPACE_ROOT", None)
        else:
            os.environ["HIFY_WORKSPACE_ROOT"] = self._previous_workspace_root
        if self._previous_memory_root is None:
            os.environ.pop("HIFY_AI_ASSISTANT_MEMORY_ROOT", None)
        else:
            os.environ["HIFY_AI_ASSISTANT_MEMORY_ROOT"] = self._previous_memory_root
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._workspace_dir.cleanup()
        self._memory_dir.cleanup()

    def test_later_session_reads_only_own_rolling_memory_md_after_reload(self) -> None:
        alice_headers = {"X-Hify-Actor-Id": "alice"}
        with TestClient(app) as client:
            session_id = client.post(
                "/api/v1/ai-assistant/sessions",
                headers=alice_headers,
                json={
                    "title": "Memory E2E",
                    "context": {
                        "aiAssistantContextBudget": {"maxContextTokens": 128},
                    },
                },
            ).json()["data"]["id"]
            started = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                headers=alice_headers,
                json={"message": "恢复上下文预算", "idempotencyKey": "memory-context-e2e"},
            ).json()["data"]
            for _ in range(100):
                run = client.get(
                    f"/api/v1/ai-assistant/runs/{started['runId']}",
                    headers=alice_headers,
                ).json()["data"]
                if run["status"] == "COMPLETED":
                    break
                time.sleep(0.02)
            snapshot = client.get(
                f"/api/v1/ai-assistant/runs/{started['runId']}/snapshot",
                headers=alice_headers,
            ).json()["data"]

        with TestClient(app) as reloaded_client:
            later_session_id = reloaded_client.post(
                "/api/v1/ai-assistant/sessions",
                headers=alice_headers,
                json={"title": "Later session"},
            ).json()["data"]["id"]
            later_turn = reloaded_client.post(
                f"/api/v1/ai-assistant/sessions/{later_session_id}/messages",
                headers=alice_headers,
                json={"message": "读取长期记忆", "idempotencyKey": "later-memory"},
            ).json()["data"]
            inspector = reloaded_client.get(
                f"/api/v1/ai-assistant/runs/{later_turn['runId']}/inspector",
                headers=alice_headers,
            ).json()["data"]
            bob_session_id = reloaded_client.post(
                "/api/v1/ai-assistant/sessions",
                headers={"X-Hify-Actor-Id": "bob"},
                json={"title": "Bob session"},
            ).json()["data"]["id"]
            bob_turn = reloaded_client.post(
                f"/api/v1/ai-assistant/sessions/{bob_session_id}/messages",
                headers={"X-Hify-Actor-Id": "bob"},
                json={"message": "读取长期记忆", "idempotencyKey": "bob-memory"},
            ).json()["data"]
            bob_inspector = reloaded_client.get(
                f"/api/v1/ai-assistant/runs/{bob_turn['runId']}/inspector",
                headers={"X-Hify-Actor-Id": "bob"},
            ).json()["data"]

        projected = inspector["memory"]["workingMemory"][0]["value"]
        self.assertEqual(run["status"], "COMPLETED")
        self.assertEqual(snapshot["run"]["status"], "COMPLETED")
        self.assertEqual(snapshot["inspector"]["contextBudget"]["usage"]["maxTokens"], 128)
        self.assertTrue(snapshot["inspector"]["contextBudget"]["selectedLayers"])
        self.assertIn("Current durable preference.", projected)
        self.assertNotIn("Expired durable preference.", projected)
        self.assertEqual(bob_inspector["memory"]["workingMemory"], [])

    def _seed_memory(self) -> None:
        from app.modules.ai_assistant.domain.access_scope import access_scope_for_workspace
        from app.modules.ai_assistant.domain.markdown_memory import MarkdownMemoryStore, MemoryScopeResolver

        access_scope = access_scope_for_workspace(
            trusted_user_id="alice",
            trusted_workspace_root=self._workspace_dir.name,
        )
        resolver = MemoryScopeResolver(self._memory_dir.name)
        try:
            scope = resolver.resolve(
                trusted_user_id=access_scope.user_id,
                trusted_workspace_id=access_scope.workspace_id,
            )
            store = MarkdownMemoryStore(resolver)
            today = date.today()
            store.merge_today(scope, facts=["Expired durable preference."], today=today - timedelta(days=30))
            store.merge_today(scope, facts=["Current durable preference."], today=today)
        finally:
            resolver.close()

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
