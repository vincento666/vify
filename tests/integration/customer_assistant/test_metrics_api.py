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


class CustomerAssistantMetricsApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self._database = mysql8_unittest_database(self, "customer_assistant_metrics")
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        with self._factory() as session:
            repository = CustomerAssistantRepository(session)
            assistant_session = repository.create_session(
                {
                    "demoSeed": "077",
                    "customer": {"phone": "13812345678"},
                }
            )
            self._session_id = int(assistant_session["id"])
            run, _ = repository.create_run(
                self._session_id,
                "metrics-red",
                "metrics-red-hash",
                {"message": "客户手机号 13812345678 要处理订单 MU5137-8899"},
            )
            running = repository.upsert_task(
                self._session_id,
                "baggage_service:CA1301",
                "BAGGAGE",
                "CA1301",
                "chatflow_sop",
                "baggage_service",
                status="RUNNING",
            )
            failed = repository.upsert_task(
                self._session_id,
                "refund_ticket:MU5137-8899",
                "REFUND",
                "MU5137-8899",
                "chatflow_sop",
                "refund_ticket",
                input_snapshot={"phone": "13812345678", "orderNo": "MU5137-8899"},
                status="FAILED",
            )
            repository.update_task(
                int(failed["id"]),
                status="FAILED",
                last_result={
                    "error": "refund failed for MU5137-8899 phone 13812345678 api_key=sk-demo",
                    "details": {"token": "secret-token"},
                },
            )
            repository.append_event(
                self._session_id,
                "worker_started",
                {"taskId": int(running["id"])},
                run_id=int(run["id"]),
                task_id=int(running["id"]),
                source="chatflow_sop",
            )
            repository.append_event(
                self._session_id,
                "task_failed",
                {"reason": "tool error for MU5137-8899 phone 13812345678 token=secret-token"},
                run_id=int(run["id"]),
                task_id=int(failed["id"]),
                source="chatflow_sop",
            )
            pending = repository.upsert_proposed_action(
                self._session_id,
                int(run["id"]),
                int(failed["id"]),
                "metrics:pending",
                "submit_refund",
                "提交退票申请",
                {"orderNo": "MU5137-8899", "token": "secret-token"},
            )
            confirmed = repository.upsert_proposed_action(
                self._session_id,
                int(run["id"]),
                int(failed["id"]),
                "metrics:confirmed",
                "submit_refund",
                "确认退票申请",
                {"orderNo": "MU5137-8899"},
            )
            rejected = repository.upsert_proposed_action(
                self._session_id,
                int(run["id"]),
                int(failed["id"]),
                "metrics:rejected",
                "submit_refund",
                "拒绝退票申请",
                {"orderNo": "MU5137-8899"},
            )
            executed = repository.upsert_proposed_action(
                self._session_id,
                int(run["id"]),
                int(failed["id"]),
                "metrics:executed",
                "submit_refund",
                "已执行退票申请",
                {"orderNo": "MU5137-8899"},
            )
            repository.update_proposed_action_status(int(confirmed["id"]), "CONFIRMED")
            repository.update_proposed_action_status(int(rejected["id"]), "REJECTED")
            repository.update_proposed_action_status(int(executed["id"]), "EXECUTED")
            self._pending_action_id = int(pending["id"])
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(runtime_lab_sop_chatflow_ids=None)

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_returns_session_observability_metrics(self) -> None:
        with TestClient(app) as client:
            response = client.get(f"/api/v1/customer-assistant/sessions/{self._session_id}/metrics")

        self.assertEqual(response.status_code, 200, response.text)
        metrics = response.json()["data"]
        self.assertEqual(metrics["sessionId"], self._session_id)
        self.assertEqual(metrics["taskStatusCounts"]["RUNNING"], 1)
        self.assertEqual(metrics["taskStatusCounts"]["FAILED"], 1)
        self.assertEqual(metrics["proposedActionStatusCounts"]["PENDING"], 1)
        self.assertEqual(metrics["proposedActionStatusCounts"]["CONFIRMED"], 1)
        self.assertEqual(metrics["proposedActionStatusCounts"]["REJECTED"], 1)
        self.assertEqual(metrics["proposedActionStatusCounts"]["EXECUTED"], 1)
        self.assertEqual(metrics["humanConfirmation"]["pending"], 1)
        self.assertEqual(metrics["humanConfirmation"]["adopted"], 2)
        self.assertEqual(metrics["humanConfirmation"]["terminal"], 3)
        self.assertAlmostEqual(metrics["humanConfirmation"]["adoptionRate"], 0.667, places=3)
        self.assertEqual(metrics["eventCounts"]["total"], 2)
        self.assertEqual(metrics["eventCounts"]["byType"]["task_failed"], 1)

    def test_metrics_redact_sensitive_failure_reason_values(self) -> None:
        with TestClient(app) as client:
            response = client.get(f"/api/v1/customer-assistant/sessions/{self._session_id}/metrics")

        self.assertEqual(response.status_code, 200, response.text)
        serialized = json.dumps(response.json()["data"], ensure_ascii=False)
        self.assertNotIn("13812345678", serialized)
        self.assertNotIn("MU5137-8899", serialized)
        self.assertNotIn("sk-demo", serialized)
        self.assertNotIn("secret-token", serialized)
        failure = response.json()["data"]["recentFailureReasons"][0]
        self.assertEqual(failure["taskType"], "REFUND")
        self.assertIn("[REDACTED]", failure["reason"])
        self.assertIn("api_key=***", failure["reason"])

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session
