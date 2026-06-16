import tempfile
import unittest
from collections.abc import Generator
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import Base, get_session
from app.main import app
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository


class CustomerAssistantProposedActionEditApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmp_dir.name) / "customer_assistant_proposed_action_edit.db"
        self._engine = create_engine(f"sqlite:///{db_path}", future=True)
        Base.metadata.create_all(bind=self._engine)
        self._factory = sessionmaker(bind=self._engine, autoflush=False, autocommit=False, expire_on_commit=False)
        with self._factory() as session:
            repository = CustomerAssistantRepository(session)
            assistant_session = repository.create_session({"case": "proposed-action-edit"})
            self._session_id = int(assistant_session["id"])
            run, _ = repository.create_run(
                session_id=self._session_id,
                idempotency_key="proposed-action-edit",
                request_hash="proposed-action-edit",
                input_payload={"source": "test"},
            )
            action = repository.upsert_proposed_action(
                session_id=self._session_id,
                run_id=int(run["id"]),
                task_id=None,
                action_key="refund_ticket:submit_refund:TK-100",
                action_type="submit_refund",
                title="提交退票申请",
                payload={"orderNo": "TK-100", "amount": 500},
            )
            self._action_id = int(action["id"])
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(runtime_lab_sop_chatflow_ids=None)

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_modifies_pending_proposed_action_and_records_audit_event(self) -> None:
        with TestClient(app) as client:
            response = client.patch(
                f"/api/v1/customer-assistant/proposed-actions/{self._action_id}",
                json={
                    "title": "提交退票申请（金额已修正）",
                    "payload": {"orderNo": "TK-100", "amount": 300, "operatorNote": "customer corrected fee"},
                },
            )
            self.assertEqual(response.status_code, 200, response.text)
            action = response.json()["data"]
            events = client.get(f"/api/v1/customer-assistant/sessions/{self._session_id}/events").json()["data"][
                "list"
            ]

        self.assertEqual(action["status"], "PENDING")
        self.assertEqual(action["title"], "提交退票申请（金额已修正）")
        self.assertEqual(action["payload"]["amount"], 300)
        modified = next(event for event in events if event["type"] == "proposed_action_modified")
        self.assertEqual(modified["payload"]["actionId"], self._action_id)
        self.assertEqual(modified["payload"]["actionType"], "submit_refund")
        self.assertEqual(set(modified["payload"]["changedFields"]), {"title", "payload"})

    def test_rejects_modifying_non_pending_proposed_action(self) -> None:
        with TestClient(app) as client:
            confirm = client.post(f"/api/v1/customer-assistant/proposed-actions/{self._action_id}/confirm")
            self.assertEqual(confirm.status_code, 200, confirm.text)
            response = client.patch(
                f"/api/v1/customer-assistant/proposed-actions/{self._action_id}",
                json={"payload": {"orderNo": "TK-100", "amount": 300}},
            )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("pending", response.text.lower())

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session
