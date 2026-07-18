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
from app.modules.ai_assistant.domain.tools import ToolRegistry
from app.modules.ai_assistant.infra.repository import AiAssistantRepository
from app.modules.ai_assistant.web.router import get_ai_assistant_service
from tests.support.mysql import mysql8_unittest_database


class AiAssistantSkillRuntimeE2ETest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_skill_runtime_e2e",
            tables=ai_assistant_tables(),
            register=register_ai_assistant_tables,
        )
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        self._skill_root = tempfile.TemporaryDirectory()
        _write_skill_tree(Path(self._skill_root.name))
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)
        app.dependency_overrides[get_ai_assistant_service] = self._service_override

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_ai_assistant_service, None)
        self._engine.dispose()
        self._skill_root.cleanup()

    def test_skill_load_is_recoverable_from_snapshot_result_and_event_replay(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/ai-assistant/sessions", json={"title": "Skill runtime E2E"})
            session_id = created.json()["data"]["id"]
            turn = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "Use tdd skill",
                    "idempotencyKey": "skill-runtime-e2e",
                    "approvalMode": "always_approve",
                    "toolName": "invoke_skill",
                    "toolInput": {"skillName": "tdd", "instruction": "Use it."},
                },
            )
            run_id = turn.json()["data"]["runId"]
            snapshot = client.get(f"/api/v1/ai-assistant/runs/{run_id}/snapshot").json()["data"]
            result = client.get(f"/api/v1/ai-assistant/runs/{run_id}/result").json()["data"]
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events").json()["data"]["list"]

        self.assertEqual(turn.status_code, 200, turn.text)
        self.assertEqual(snapshot["run"]["status"], "COMPLETED")
        self.assertEqual(result["toolCalls"][0]["output"]["status"], "LOADED")
        self.assertEqual(snapshot["inspector"]["toolCalls"][0]["output"]["metadata"]["name"], "tdd")
        self.assertIn("BODY_SECRET", result["toolCalls"][0]["output"]["skillMarkdown"])
        self.assertIn("skill.loaded", [event["type"] for event in events])

    def _service_override(self) -> Generator[AiAssistantHarnessService, None, None]:
        from app.modules.ai_assistant.domain.skills import SkillRuntime

        with self._factory() as session:
            yield AiAssistantHarnessService(
                AiAssistantRepository(session),
                tool_registry=ToolRegistry.with_demo_tools(),
                skill_runtime=SkillRuntime(root_paths=[Path(self._skill_root.name)]),
            )

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session


def _write_skill_tree(root: Path) -> None:
    skill_dir = root / "tdd"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: tdd
description: Use red-green-refactor workflow.
version: 1.2.3
risk: READ
triggers:
  - tdd
---
# TDD Skill

BODY_SECRET: e2e load marker.
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
