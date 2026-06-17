import json
import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository
from tests.support.mysql import mysql8_unittest_database


class CustomerAssistantProposedActionDecisionNotesTest(unittest.TestCase):
    def setUp(self) -> None:
        self._database = mysql8_unittest_database(self, "customer_assistant_action_decision_notes")
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        with self._factory() as session:
            repository = CustomerAssistantRepository(session)
            assistant_session = repository.create_session({"case": "decision-notes"})
            self._session_id = int(assistant_session["id"])
            run, _ = repository.create_run(
                self._session_id,
                "decision-notes",
                "decision-notes-hash",
                {"message": "confirm and reject with decision notes"},
            )
            confirm_action = repository.upsert_proposed_action(
                self._session_id,
                int(run["id"]),
                None,
                "decision-notes:confirm",
                "submit_refund",
                "Submit refund",
                {"orderNo": "TK-143"},
            )
            reject_action = repository.upsert_proposed_action(
                self._session_id,
                int(run["id"]),
                None,
                "decision-notes:reject",
                "submit_refund",
                "Reject refund",
                {"orderNo": "TK-144"},
            )
            self._confirm_action_id = int(confirm_action["id"])
            self._reject_action_id = int(reject_action["id"])
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(runtime_lab_sop_chatflow_ids=None)

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_confirm_note_and_reject_reason_are_sanitized_in_result_events_and_audit(self) -> None:
        note = "confirmed by phone 13800138000 for order TK-143 apiKey=note-secret"
        reason = "operator refused phone 13900139000 order TK-144 token=reject-secret"
        expected_note = "confirmed by phone [REDACTED] for order [REDACTED] apiKey=***"
        expected_reason = "operator refused phone [REDACTED] order [REDACTED] token=***"

        with TestClient(app) as client:
            confirmed = client.post(
                f"/api/v1/customer-assistant/proposed-actions/{self._confirm_action_id}/confirm",
                json={"note": note},
            )
            rejected = client.post(
                f"/api/v1/customer-assistant/proposed-actions/{self._reject_action_id}/reject",
                json={"reason": reason},
            )
            events = client.get(f"/api/v1/customer-assistant/sessions/{self._session_id}/events")
            audit = client.get(f"/api/v1/customer-assistant/sessions/{self._session_id}/operator-audit")

        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        self.assertEqual(rejected.status_code, 200, rejected.text)
        self.assertEqual(events.status_code, 200, events.text)
        self.assertEqual(audit.status_code, 200, audit.text)

        self.assertEqual(confirmed.json()["data"]["result"]["decision"]["note"], expected_note)
        self.assertEqual(rejected.json()["data"]["result"]["decision"]["reason"], expected_reason)

        event_rows = events.json()["data"]["list"]
        confirmed_event = next(
            event for event in event_rows if event["type"] == "proposed_action_confirmed"
        )
        rejected_event = next(event for event in event_rows if event["type"] == "proposed_action_rejected")
        self.assertEqual(confirmed_event["payload"]["decision"]["note"], expected_note)
        self.assertEqual(rejected_event["payload"]["decision"]["reason"], expected_reason)

        audit_rows = audit.json()["data"]["list"]
        confirm_audit = next(
            row for row in audit_rows if row["eventType"] == "proposed_action_confirmed"
        )
        reject_audit = next(row for row in audit_rows if row["eventType"] == "proposed_action_rejected")
        self.assertIn(f"note: {expected_note}", confirm_audit["summary"])
        self.assertIn(f"reason: {expected_reason}", reject_audit["summary"])

        public_json = json.dumps(
            {
                "confirmed": confirmed.json()["data"],
                "rejected": rejected.json()["data"],
                "events": events.json()["data"],
                "audit": audit.json()["data"],
            },
            ensure_ascii=False,
        )
        for leaked in ("13800138000", "13900139000", "TK-143", "TK-144", "note-secret", "reject-secret"):
            self.assertNotIn(leaked, public_json)

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
