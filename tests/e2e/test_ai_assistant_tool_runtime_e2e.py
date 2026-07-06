import unittest
from collections.abc import Generator
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
from app.modules.ai_assistant.domain.tools import RiskLevel, ToolManifest, ToolRegistry
from app.modules.ai_assistant.infra.repository import AiAssistantRepository
from app.modules.ai_assistant.web.router import get_ai_assistant_service
from tests.support.mysql import mysql8_unittest_database


class AiAssistantToolRuntimeE2ETest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_tool_runtime_e2e",
            tables=ai_assistant_tables(),
            register=register_ai_assistant_tables,
        )
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)
        app.dependency_overrides[get_ai_assistant_service] = self._service_override

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_ai_assistant_service, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_failed_tool_observation_is_visible_in_result_events_and_snapshot(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/ai-assistant/sessions", json={"title": "Tool runtime E2E"})
            session_id = created.json()["data"]["id"]
            turn = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "run failed tool",
                    "idempotencyKey": "tool-runtime-e2e",
                    "toolName": "unstable_tool",
                    "toolInput": {"caseId": "case-tool-e2e"},
                    "approvalMode": "always_approve",
                },
            )
            run_id = turn.json()["data"].get("runId") if turn.status_code == 200 else None
            result = client.get(f"/api/v1/ai-assistant/runs/{run_id}/result") if run_id else None
            snapshot = client.get(f"/api/v1/ai-assistant/runs/{run_id}/snapshot") if run_id else None
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events") if run_id else None

        self.assertEqual(turn.status_code, 200, turn.text)
        self.assertEqual(turn.json()["data"]["status"], "FAILED")
        self.assertEqual(result.json()["data"]["status"], "FAILED")
        observation = result.json()["data"]["toolCalls"][0]["output"]["observation"]
        self.assertEqual(observation["error"]["code"], "TOOL_RUNTIME_ERROR")
        self.assertEqual(snapshot.json()["data"]["inspector"]["toolCalls"][0]["output"]["observation"], observation)
        event_types = [event["type"] for event in events.json()["data"]["list"]]
        self.assertIn("tool.error_observation", event_types)
        self.assertIn("plan.revised", event_types)
        self.assertIn("tool.call_failed", event_types)
        self.assertIn("plan.blocked", event_types)
        self.assertIn("task.blocked", event_types)
        self.assertIn("run.failed", event_types)
        after_tool_start = event_types[event_types.index("tool.call_started") :]
        self.assertNotIn("tool.call_completed", after_tool_start)
        self.assertNotIn("plan.step_completed", after_tool_start)
        self.assertNotIn("task.completed", after_tool_start)
        self.assertNotIn("run.completed", after_tool_start)

    def _service_override(self) -> Generator[AiAssistantHarnessService, None, None]:
        with self._factory() as session:
            yield AiAssistantHarnessService(
                AiAssistantRepository(session),
                tool_registry=ToolRegistry({"unstable_tool": (_unstable_manifest(), _unstable_tool)}),
            )

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session


def _unstable_tool(_payload: dict[str, Any]):
    raise RuntimeError("simulated 5xx")


def _unstable_manifest() -> ToolManifest:
    return ToolManifest(
        name="unstable_tool",
        description="Tool that simulates a transient backend failure.",
        input_schema={"type": "object", "properties": {"caseId": {"type": "string"}}},
        output_schema={"type": "object"},
        timeout_ms=50,
        risk_level=RiskLevel.READ,
        read_resources=[],
        write_resources=[],
        policy_ref="ai_assistant_read_only",
    )


if __name__ == "__main__":
    unittest.main()
