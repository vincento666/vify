import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository
from tests.support.mysql import mysql8_unittest_database


class CustomerAssistantProposedActionOperatorAttributionTest(unittest.TestCase):
    def setUp(self) -> None:
        self._database = mysql8_unittest_database(self, "customer_assistant_action_operator_attribution")
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        with self._factory() as session:
            repository = CustomerAssistantRepository(session)
            assistant_session = repository.create_session({"customer": {"name": "Attribution Test"}})
            self._session_id = int(assistant_session["id"])
            run, _ = repository.create_run(
                self._session_id,
                "operator-attribution",
                "operator-attribution-hash",
                {"message": "confirm and execute"},
            )
            task = repository.upsert_task(
                self._session_id,
                "refund_ticket:TK-141",
                "REFUND",
                "TK-141",
                "chatflow_sop",
                "refund_ticket",
                status="WAITING",
            )
            execute_action = repository.upsert_proposed_action(
                self._session_id,
                int(run["id"]),
                int(task["id"]),
                "operator-attribution:execute",
                "submit_refund",
                "提交退票申请",
                {"orderNo": "TK-141"},
            )
            reject_action = repository.upsert_proposed_action(
                self._session_id,
                int(run["id"]),
                int(task["id"]),
                "operator-attribution:reject",
                "submit_refund",
                "拒绝退票申请",
                {"orderNo": "TK-142"},
            )
            self._execute_action_id = int(execute_action["id"])
            self._reject_action_id = int(reject_action["id"])
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(runtime_lab_sop_chatflow_ids=None)

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_confirm_reject_and_execute_events_are_operator_attributed(self) -> None:
        with TestClient(app) as client:
            confirmed = client.post(f"/api/v1/customer-assistant/proposed-actions/{self._execute_action_id}/confirm")
            executed = client.post(f"/api/v1/customer-assistant/proposed-actions/{self._execute_action_id}/execute")
            rejected = client.post(f"/api/v1/customer-assistant/proposed-actions/{self._reject_action_id}/reject")
            events = client.get(f"/api/v1/customer-assistant/sessions/{self._session_id}/events")
            audit = client.get(f"/api/v1/customer-assistant/sessions/{self._session_id}/operator-audit")

        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        self.assertEqual(executed.status_code, 200, executed.text)
        self.assertEqual(rejected.status_code, 200, rejected.text)
        self.assertEqual(events.status_code, 200, events.text)
        self.assertEqual(audit.status_code, 200, audit.text)

        event_rows = [
            event
            for event in events.json()["data"]["list"]
            if event["type"]
            in {
                "proposed_action_confirmed",
                "proposed_action_rejected",
                "proposed_action_executing",
                "proposed_action_executed",
            }
        ]
        self.assertEqual(
            [event["type"] for event in event_rows],
            [
                "proposed_action_confirmed",
                "proposed_action_executing",
                "proposed_action_executed",
                "proposed_action_rejected",
            ],
        )
        self.assertTrue(all(event["actor"] == "operator" for event in event_rows))
        self.assertTrue(all(event["source"] == "operator_advisory" for event in event_rows))

        audit_rows = [
            row
            for row in audit.json()["data"]["list"]
            if row["eventType"]
            in {
                "proposed_action_confirmed",
                "proposed_action_rejected",
                "proposed_action_executing",
                "proposed_action_executed",
            }
        ]
        self.assertTrue(audit_rows)
        self.assertTrue(all(row["actor"] == "operator" for row in audit_rows))
        self.assertTrue(all(row["source"] == "operator_advisory" for row in audit_rows))

    def test_host_actor_is_recorded_for_confirm_reject_and_execute_audit(self) -> None:
        headers = _host_headers("agent-007")

        with TestClient(app) as client:
            assistant_session = client.post(
                "/api/v1/customer-assistant/sessions",
                json={"context": {"customer": {"name": "Host Actor Test"}}},
                headers=headers,
            )
            self.assertEqual(assistant_session.status_code, 200, assistant_session.text)
            session_id = int(assistant_session.json()["data"]["id"])
            execute_action_id, reject_action_id = self._create_actions(session_id)

            confirmed = client.post(
                f"/api/v1/customer-assistant/proposed-actions/{execute_action_id}/confirm",
                headers=headers,
            )
            executed = client.post(
                f"/api/v1/customer-assistant/proposed-actions/{execute_action_id}/execute",
                headers=headers,
            )
            rejected = client.post(
                f"/api/v1/customer-assistant/proposed-actions/{reject_action_id}/reject",
                headers=headers,
            )
            events = client.get(f"/api/v1/customer-assistant/sessions/{session_id}/events", headers=headers)
            audit = client.get(
                f"/api/v1/customer-assistant/sessions/{session_id}/operator-audit",
                headers=headers,
            )

        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        self.assertEqual(executed.status_code, 200, executed.text)
        self.assertEqual(rejected.status_code, 200, rejected.text)

        event_rows = [
            event
            for event in events.json()["data"]["list"]
            if event["type"]
            in {
                "proposed_action_confirmed",
                "proposed_action_rejected",
                "proposed_action_executing",
                "proposed_action_executed",
            }
        ]
        self.assertTrue(event_rows)
        self.assertTrue(all(event["actor"] == "agent-007" for event in event_rows))

        audit_rows = [
            row
            for row in audit.json()["data"]["list"]
            if row["eventType"]
            in {
                "proposed_action_confirmed",
                "proposed_action_rejected",
                "proposed_action_executing",
                "proposed_action_executed",
            }
        ]
        self.assertTrue(audit_rows)
        self.assertTrue(all(row["actor"] == "agent-007" for row in audit_rows))

    def _create_actions(self, session_id: int) -> tuple[int, int]:
        with self._factory() as session:
            repository = CustomerAssistantRepository(session)
            run, _ = repository.create_run(
                session_id,
                "host-actor-attribution",
                "host-actor-attribution-hash",
                {"message": "confirm and execute with host actor"},
            )
            task = repository.upsert_task(
                session_id,
                "refund_ticket:TK-155",
                "REFUND",
                "TK-155",
                "chatflow_sop",
                "refund_ticket",
                status="WAITING",
            )
            execute_action = repository.upsert_proposed_action(
                session_id,
                int(run["id"]),
                int(task["id"]),
                "host-actor-attribution:execute",
                "submit_refund",
                "提交退票申请",
                {"orderNo": "TK-155"},
            )
            reject_action = repository.upsert_proposed_action(
                session_id,
                int(run["id"]),
                int(task["id"]),
                "host-actor-attribution:reject",
                "submit_refund",
                "拒绝退票申请",
                {"orderNo": "TK-156"},
            )
        return int(execute_action["id"]), int(reject_action["id"])

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session


def _host_headers(actor_id: str) -> dict[str, str]:
    return {
        "X-Hify-Actor-Id": actor_id,
        "X-Hify-Actor-Name": f"Agent {actor_id}",
        "X-Hify-Tenant-Id": "tenant-action-audit",
        "X-Hify-Org-Id": "tenant-action-audit",
        "X-Hify-Source": "embedded-demo-shell",
        "X-Hify-Permissions": "customer_assistant:read,customer_assistant:operate",
    }


if __name__ == "__main__":
    unittest.main()
