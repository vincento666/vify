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


class CustomerAssistantDraftDeliveryOutboxApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self._database = mysql8_unittest_database(self, "customer_assistant_draft_delivery")
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        with self._factory() as session:
            repository = CustomerAssistantRepository(session)
            assistant_session = repository.create_session(
                {
                    "case": "draft-delivery",
                    "customer": {"phone": "13812345678"},
                    "apiToken": "raw-api-token",
                }
            )
            self._session_id = int(assistant_session["id"])
            run, _ = repository.create_run(
                session_id=self._session_id,
                idempotency_key="draft-delivery-run",
                request_hash="draft-delivery-run",
                input_payload={"message": "客户 13812345678 询问订单 MU5137-8899 token=secret-token"},
            )
            sent_action = repository.upsert_proposed_action(
                session_id=self._session_id,
                run_id=int(run["id"]),
                task_id=None,
                action_key="draft-delivery:send:MU5137-8899",
                action_type="send_customer_message",
                title="发送客户回复草稿",
                payload={
                    "channel": "mock_web",
                    "conversationId": "conversation-MU5137-8899",
                    "recipient": {"phone": "13812345678"},
                    "draft": "您好，订单 MU5137-8899 已为您处理。token=secret-token",
                    "metadata": {"apiToken": "raw-api-token"},
                },
            )
            failed_action = repository.upsert_proposed_action(
                session_id=self._session_id,
                run_id=int(run["id"]),
                task_id=None,
                action_key="draft-delivery:fail:MU5137-8899",
                action_type="send_customer_message",
                title="发送客户回复草稿（失败演练）",
                payload={
                    "channel": "mock_web",
                    "conversationId": "conversation-MU5137-8899",
                    "recipient": {"phone": "13812345678"},
                    "draft": "您好，订单 MU5137-8899 暂时发送失败。token=secret-token",
                    "mockDelivery": {"forceFailure": True},
                },
            )
            repository.update_proposed_action_status(int(sent_action["id"]), "CONFIRMED")
            repository.update_proposed_action_status(int(failed_action["id"]), "CONFIRMED")
            self._sent_action_id = int(sent_action["id"])
            self._failed_action_id = int(failed_action["id"])
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(runtime_lab_sop_chatflow_ids=None)

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_delivers_confirmed_reply_draft_through_mock_outbox_and_redacts_surfaces(self) -> None:
        with TestClient(app) as client:
            response = client.post(f"/api/v1/customer-assistant/proposed-actions/{self._sent_action_id}/deliver")
            self.assertEqual(response.status_code, 200, response.text)
            delivered = response.json()["data"]
            actions = client.get(f"/api/v1/customer-assistant/sessions/{self._session_id}/proposed-actions").json()[
                "data"
            ]["list"]
            events = client.get(f"/api/v1/customer-assistant/sessions/{self._session_id}/events").json()["data"][
                "list"
            ]
            audit = client.get(f"/api/v1/customer-assistant/sessions/{self._session_id}/operator-audit").json()[
                "data"
            ]["list"]

        self.assertEqual(delivered["status"], "SENT")
        self.assertEqual(delivered["result"]["delivery"]["adapterRef"], "customer_reply_mock_channel")
        self.assertEqual(delivered["result"]["delivery"]["channel"], "mock_web")
        self.assertEqual(delivered["result"]["delivery"]["status"], "SENT")
        self.assertTrue(str(delivered["result"]["delivery"]["messageId"]).startswith("mock-msg-"))
        listed = next(action for action in actions if action["id"] == self._sent_action_id)
        self.assertEqual(listed["status"], "SENT")
        delivered_event = next(event for event in events if event["type"] == "draft_delivery_sent")
        self.assertEqual(delivered_event["payload"]["actionId"], self._sent_action_id)
        self.assertEqual(delivered_event["payload"]["status"], "SENT")
        self.assertIn("draft_delivery_started", [event["type"] for event in events])
        audit_row = next(item for item in audit if item["eventType"] == "draft_delivery_sent")
        self.assertEqual(audit_row["status"], "SENT")
        self.assertEqual(audit_row["targetType"], "action")
        self.assertEqual(audit_row["targetId"], self._sent_action_id)
        serialized = json.dumps(
            {"delivered": delivered, "actions": actions, "events": events, "audit": audit},
            ensure_ascii=False,
        )
        self.assertNotIn("13812345678", serialized)
        self.assertNotIn("MU5137-8899", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("raw-api-token", serialized)

    def test_persists_failed_delivery_when_mock_adapter_declines_send(self) -> None:
        with TestClient(app) as client:
            response = client.post(f"/api/v1/customer-assistant/proposed-actions/{self._failed_action_id}/deliver")
            self.assertEqual(response.status_code, 200, response.text)
            failed = response.json()["data"]
            events = client.get(f"/api/v1/customer-assistant/sessions/{self._session_id}/events").json()["data"][
                "list"
            ]
            audit = client.get(f"/api/v1/customer-assistant/sessions/{self._session_id}/operator-audit").json()[
                "data"
            ]["list"]

        self.assertEqual(failed["status"], "FAILED")
        self.assertEqual(failed["result"]["delivery"]["adapterRef"], "customer_reply_mock_channel")
        self.assertEqual(failed["result"]["delivery"]["status"], "FAILED")
        self.assertEqual(failed["result"]["error"]["code"], "MOCK_DELIVERY_FAILED")
        failed_event = next(event for event in events if event["type"] == "draft_delivery_failed")
        self.assertEqual(failed_event["payload"]["actionId"], self._failed_action_id)
        self.assertEqual(failed_event["payload"]["status"], "FAILED")
        audit_row = next(item for item in audit if item["eventType"] == "draft_delivery_failed")
        self.assertEqual(audit_row["status"], "FAILED")
        serialized = json.dumps({"failed": failed, "events": events, "audit": audit}, ensure_ascii=False)
        self.assertNotIn("13812345678", serialized)
        self.assertNotIn("MU5137-8899", serialized)
        self.assertNotIn("secret-token", serialized)

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
