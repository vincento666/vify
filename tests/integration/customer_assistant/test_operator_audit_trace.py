import json
import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from tests.support.mysql import mysql8_unittest_database
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository


class CustomerAssistantOperatorAuditTraceTest(unittest.TestCase):
    def setUp(self) -> None:
        self._database = mysql8_unittest_database(self, "customer_assistant_operator_audit")
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        with self._factory() as session:
            repository = CustomerAssistantRepository(session)
            assistant_session = repository.create_session(
                {
                    "demoSeed": "103",
                    "customer": {"phone": "13812345678"},
                    "orderNo": "MU5137-8899",
                    "apiToken": "raw-api-token",
                }
            )
            self._session_id = int(assistant_session["id"])
            run, _ = repository.create_run(
                self._session_id,
                "audit-red",
                "audit-red-hash",
                {"message": "客户 13812345678 订单 MU5137-8899 token=secret-token"},
            )
            task = repository.upsert_task(
                self._session_id,
                "refund_ticket:MU5137-8899",
                "REFUND",
                "MU5137-8899",
                "chatflow_sop",
                "refund_ticket",
                input_snapshot={"phone": "13812345678", "orderNo": "MU5137-8899"},
                status="RUNNING",
            )
            action = repository.upsert_proposed_action(
                self._session_id,
                int(run["id"]),
                int(task["id"]),
                "audit:refund",
                "submit_refund",
                "提交退票申请",
                {"orderNo": "MU5137-8899", "token": "secret-token"},
            )
            repository.append_event(
                self._session_id,
                "task_control_proposed",
                {
                    "actionId": int(action["id"]),
                    "controlType": "retry",
                    "reason": "operator retry for MU5137-8899 phone 13812345678 token=secret-token",
                    "taskId": int(task["id"]),
                    "taskKey": "refund_ticket:MU5137-8899",
                },
                run_id=int(run["id"]),
                task_id=int(task["id"]),
                source="operator_advisory",
                actor="operator",
            )
            repository.append_event(
                self._session_id,
                "proposed_action_confirmed",
                {"actionId": int(action["id"]), "actionType": "submit_refund", "orderNo": "MU5137-8899"},
                run_id=int(run["id"]),
                task_id=int(task["id"]),
                source="operator_advisory",
                actor="operator",
            )
            repository.append_event(
                self._session_id,
                "proposed_action_executed",
                {
                    "actionId": int(action["id"]),
                    "actionType": "submit_refund",
                    "status": "EXECUTED",
                    "result": {"audit": {"orderNo": "MU5137-8899", "token": "secret-token"}},
                },
                run_id=int(run["id"]),
                task_id=int(task["id"]),
                source="operator_advisory",
                actor="operator",
            )
            repository.append_event(
                self._session_id,
                "operator_advisory_context_packed",
                {
                    "turnMode": "operator_recommendation_turn",
                    "taskCount": 1,
                    "knowledgeSnippetCount": 2,
                    "warnings": ["contains order MU5137-8899 and phone 13812345678"],
                },
                run_id=int(run["id"]),
                source="operator_advisory",
                actor="operator",
            )
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(runtime_lab_sop_chatflow_ids=None)

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_operator_audit_trace_returns_redacted_whitelisted_rows(self) -> None:
        with TestClient(app) as client:
            response = client.get(f"/api/v1/customer-assistant/sessions/{self._session_id}/operator-audit")

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["sessionId"], self._session_id)
        self.assertEqual(data["total"], 4)
        event_types = [item["eventType"] for item in data["list"]]
        self.assertEqual(
            event_types,
            [
                "task_control_proposed",
                "proposed_action_confirmed",
                "proposed_action_executed",
                "operator_advisory_context_packed",
            ],
        )
        row_keys = set(data["list"][0].keys())
        self.assertEqual(
            row_keys,
            {
                "id",
                "sequence",
                "eventType",
                "title",
                "actor",
                "source",
                "status",
                "targetType",
                "targetId",
                "summary",
                "createdAt",
            },
        )
        serialized = json.dumps(data, ensure_ascii=False)
        self.assertNotIn("13812345678", serialized)
        self.assertNotIn("MU5137-8899", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("raw-api-token", serialized)
        self.assertNotIn("payload", serialized)
        self.assertIn("[REDACTED]", serialized)

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
