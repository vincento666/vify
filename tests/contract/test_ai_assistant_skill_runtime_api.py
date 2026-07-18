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


class AiAssistantSkillRuntimeApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_skill_runtime_contract",
            tables=ai_assistant_tables(),
            register=register_ai_assistant_tables,
        )
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        self._skill_root = tempfile.TemporaryDirectory()
        _write_skill_tree(Path(self._skill_root.name))
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(
            _env_file=None,
            ai_assistant_tool_profile="demo",
        )
        app.dependency_overrides[get_ai_assistant_service] = self._service_override

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_ai_assistant_service, None)
        self._engine.dispose()
        self._skill_root.cleanup()

    def test_invoke_skill_loads_markdown_and_requested_resource_with_audit_events(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/ai-assistant/sessions", json={"title": "Skill runtime"})
            session_id = created.json()["data"]["id"]
            turn = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "Use tdd skill and read its checklist",
                    "idempotencyKey": "skill-runtime-contract",
                    "approvalMode": "always_approve",
                    "toolName": "invoke_skill",
                    "toolInput": {
                        "skillName": "tdd",
                        "instruction": "Use the checklist.",
                        "resources": ["references/checklist.md"],
                    },
                },
            )
            run_id = turn.json()["data"]["runId"]
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events").json()["data"]["list"]
            inspector = client.get(f"/api/v1/ai-assistant/runs/{run_id}/inspector").json()["data"]

        self.assertEqual(turn.status_code, 200, turn.text)
        data = turn.json()["data"]
        self.assertEqual(data["status"], "COMPLETED")
        tool_output = data["toolCalls"][0]["output"]
        self.assertEqual(tool_output["status"], "LOADED")
        self.assertEqual(tool_output["metadata"]["name"], "tdd")
        self.assertEqual(tool_output["metadata"]["version"], "1.2.3")
        self.assertTrue(tool_output["metadata"]["checksum"].startswith("sha256:"))
        self.assertIn("BODY_SECRET", tool_output["skillMarkdown"])
        self.assertEqual(tool_output["resources"][0]["path"], "references/checklist.md")
        self.assertIn("RED then GREEN", tool_output["resources"][0]["content"])
        event_types = [event["type"] for event in events]
        self.assertIn("skill.loaded", event_types)
        self.assertIn("skill.resource_read", event_types)
        skill_loaded = next(event for event in events if event["type"] == "skill.loaded")
        self.assertEqual(skill_loaded["payload"]["riskLevel"], "READ")
        self.assertEqual(inspector["toolCalls"][0]["output"]["metadata"]["name"], "tdd")

    def test_skill_script_tool_requires_policy_approval_before_invocation(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/ai-assistant/sessions", json={"title": "Skill script risk"})
            session_id = created.json()["data"]["id"]
            turn = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "Run the tdd verifier script",
                    "idempotencyKey": "skill-script-contract",
                    "approvalMode": "smart_approval",
                    "toolName": "run_skill_script",
                    "toolInput": {"skillName": "tdd", "scriptPath": "scripts/verify.js"},
                },
            )
            run_id = turn.json()["data"]["runId"]
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events").json()["data"]["list"]

        self.assertEqual(turn.status_code, 200, turn.text)
        data = turn.json()["data"]
        self.assertEqual(data["status"], "WAITING_APPROVAL")
        self.assertTrue(data["approvalRequired"])
        event_types = [event["type"] for event in events]
        self.assertIn("permission.evaluated", event_types)
        self.assertIn("approval.required", event_types)
        permission = next(event for event in events if event["type"] == "permission.evaluated")
        self.assertEqual(permission["payload"]["toolName"], "run_skill_script")
        self.assertEqual(permission["payload"]["riskLevel"], "EXTERNAL_SIDE_EFFECT")
        self.assertEqual(permission["payload"]["decision"], "require_approval")
        self.assertNotIn("skill.script_invoked", event_types)

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
    (skill_dir / "references").mkdir(parents=True)
    (skill_dir / "scripts").mkdir()
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

BODY_SECRET: loaded by invoke_skill only.
""",
        encoding="utf-8",
    )
    (skill_dir / "references" / "checklist.md").write_text("RED then GREEN then REFACTOR.\n", encoding="utf-8")
    (skill_dir / "scripts" / "verify.js").write_text("console.log('verify');\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
