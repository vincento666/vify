import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from app.modules.ai_assistant.domain import business_adapter
from app.modules.ai_assistant.domain.business_adapter import MockAviationAdapter
from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
from app.modules.ai_assistant.domain.tools import ToolRegistry
from app.modules.ai_assistant.infra.repository import AiAssistantRepository
from app.modules.ai_assistant.web.router import get_ai_assistant_service
from tests.support.mysql import mysql8_unittest_database


class AiAssistantTraceAuditApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_trace_audit_contract",
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

    def test_run_audit_export_includes_trace_budget_approval_adapter_and_final_result(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/ai-assistant/sessions", json={"title": "Audit export"})
            session_id = created.json()["data"]["id"]
            turn = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "mock refund audit",
                    "idempotencyKey": "trace-audit-export",
                    "toolName": "mock_aviation.refund",
                    "toolInput": {"caseId": "case-audit-1", "passengerId": "PAX-1", "request": "refund"},
                    "approvalMode": "smart_approval",
                    "aiAssistantBudget": {"maxUsd": 0.000001},
                    "modelBudgetPolicy": {"primaryModel": "qwen-max", "fallbackModel": "qwen-turbo"},
                },
            )
            run_id = turn.json()["data"]["runId"]
            approval_id = turn.json()["data"]["approvalId"]
            approved = client.post(
                f"/api/v1/ai-assistant/approvals/{approval_id}/approve",
                json={"actorId": "operator-audit"},
            )
            audit = client.get(f"/api/v1/ai-assistant/runs/{run_id}/audit")

        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(audit.status_code, 200, audit.text)
        data = audit.json()["data"]
        self.assertEqual(data["runId"], run_id)
        self.assertEqual(data["audit"]["plan"]["planningStrategy"], "auto_lightweight")
        self.assertEqual(data["audit"]["toolCalls"][0]["toolName"], "mock_aviation.refund")
        self.assertEqual(data["audit"]["toolCalls"][0]["args"]["caseId"], "case-audit-1")
        self.assertEqual(data["audit"]["approvals"][0]["status"], "APPROVED")
        self.assertEqual(data["audit"]["adapterAudits"][0]["adapterName"], "mock_aviation")
        self.assertTrue(data["audit"]["adapterAudits"][0]["mockOnly"])
        self.assertFalse(data["audit"]["adapterAudits"][0]["realAviationRulesApplied"])
        self.assertTrue(data["audit"]["finalResult"])
        self.assertGreaterEqual(data["budget"]["context"]["usage"]["maxTokens"], 1)
        self.assertEqual(data["budget"]["cost"]["maxUsd"], 0.000001)
        self.assertEqual(data["budget"]["policy"]["status"], "over_budget")
        self.assertEqual(data["budget"]["policy"]["model"]["action"], "degrade")
        self.assertEqual(data["budget"]["policy"]["model"]["selectedModel"], "qwen-turbo")
        self.assertIn("cost_budget_exceeded", data["budget"]["policy"]["reasons"])
        span_kinds = {span["kind"] for span in data["trace"]["spans"]}
        self.assertTrue({"run", "tool", "approval", "resource_lock", "context_budget", "business_adapter"}.issubset(span_kinds))
        self.assertFalse(data["eval"]["passed"])
        trace_check = next(check for check in data["eval"]["checks"] if check["id"] == "trace_coverage")
        self.assertIn("skill", trace_check["missingSpanKinds"])

    def _service_override(self) -> Generator[AiAssistantHarnessService, None, None]:
        with self._factory() as session:
            tools = business_adapter.tool_entries_for_business_adapter(MockAviationAdapter())
            yield AiAssistantHarnessService(
                AiAssistantRepository(session),
                tool_registry=ToolRegistry(tools),
            )

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
