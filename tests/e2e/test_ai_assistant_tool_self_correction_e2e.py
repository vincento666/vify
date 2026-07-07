import unittest
from collections.abc import Generator
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
from app.modules.ai_assistant.domain.tools import RiskLevel, ToolManifest, ToolRegistry, ToolResult
from app.modules.ai_assistant.infra.repository import AiAssistantRepository
from app.modules.ai_assistant.web.router import get_ai_assistant_service
from tests.support.mysql import mysql8_unittest_database


class AiAssistantToolSelfCorrectionE2ETest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_tool_self_correction_e2e",
            tables=ai_assistant_tables(),
            register=register_ai_assistant_tables,
        )
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        self._calls: list[dict[str, Any]] = []
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)
        app.dependency_overrides[get_ai_assistant_service] = self._service_override

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_ai_assistant_service, None)
        self._engine.dispose()

    def test_run_repairs_failed_tool_observation_and_recovers_snapshot(self) -> None:
        with TestClient(app) as client:
            session_id = client.post(
                "/api/v1/ai-assistant/sessions",
                json={"title": "Self correction E2E"},
            ).json()["data"]["id"]
            turn = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "用户要求查询 transient case 并自动修复一次工具错误",
                    "idempotencyKey": "self-correction-e2e-repair",
                    "toolName": "repairable_lookup",
                    "toolInput": {
                        "caseId": "bad",
                        "_selfCorrection": {"retryToolInput": {"caseId": "good"}},
                    },
                    "approvalMode": "always_approve",
                    "aiAssistantBudget": {"maxToolRepairAttempts": 1},
                },
            )
            run_id = turn.json()["data"].get("runId") if turn.status_code == 200 else None
            result = client.get(f"/api/v1/ai-assistant/runs/{run_id}/result") if run_id else None
            snapshot = client.get(f"/api/v1/ai-assistant/runs/{run_id}/snapshot") if run_id else None
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events") if run_id else None

        self.assertEqual(turn.status_code, 200, turn.text)
        self.assertEqual(result.json()["data"]["status"], "COMPLETED")
        self.assertEqual(result.json()["data"]["toolCalls"][0]["status"], "FAILED")
        self.assertEqual(result.json()["data"]["toolCalls"][1]["status"], "COMPLETED")
        self.assertEqual(snapshot.json()["data"]["run"]["status"], "COMPLETED")
        inspector = snapshot.json()["data"]["inspector"]
        self.assertEqual(len(inspector["toolCalls"]), 2)
        self.assertEqual(inspector["toolCalls"][0]["output"]["observation"]["error"]["code"], "TOOL_RUNTIME_ERROR")
        event_types = [event["type"] for event in events.json()["data"]["list"]]
        self.assertIn("tool.self_correction_started", event_types)
        self.assertIn("tool.self_correction_completed", event_types)
        self.assertIn("plan.revised", event_types)
        self.assertIn("task.completed", event_types)
        self.assertEqual([call["caseId"] for call in self._calls], ["bad", "bad", "good"])

    def _service_override(self) -> Generator[AiAssistantHarnessService, None, None]:
        with self._factory() as session:
            yield AiAssistantHarnessService(
                AiAssistantRepository(session),
                tool_registry=ToolRegistry({"repairable_lookup": (_read_manifest(), self._repairable_lookup)}),
            )

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session

    def _repairable_lookup(self, payload: dict[str, Any]) -> ToolResult:
        self._calls.append({"toolName": "repairable_lookup", "caseId": payload.get("caseId")})
        if payload.get("caseId") == "good":
            return ToolResult(status="COMPLETED", output={"status": "repaired", "caseId": "good"})
        raise RuntimeError("simulated 5xx")


def _read_manifest() -> ToolManifest:
    return ToolManifest(
        name="repairable_lookup",
        description="Read-only lookup that fails once until arguments are repaired.",
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
