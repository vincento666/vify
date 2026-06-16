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
from app.modules.demo.mvp_seed import seed_mvp_demo


class CustomerAssistantTaskControlApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmp_dir.name) / "customer_assistant_task_controls.db"
        self._engine = create_engine(f"sqlite:///{db_path}", future=True)
        Base.metadata.create_all(bind=self._engine)
        self._factory = sessionmaker(bind=self._engine, autoflush=False, autocommit=False, expire_on_commit=False)
        with self._factory() as session:
            seed = seed_mvp_demo(session)
            repository = CustomerAssistantRepository(session)
            self._running_session_id = seed.customer_session_ids[0]
            self._running_task_id = int(repository.list_tasks(self._running_session_id)[0]["id"])
            self._waiting_session_id = seed.customer_session_ids[1]
            self._waiting_task_id = int(repository.list_tasks(self._waiting_session_id)[0]["id"])
            failed = repository.create_session({"demoSeed": "074", "storyId": "task-control-red"})
            self._failed_session_id = int(failed["id"])
            failed_task = repository.upsert_task(
                self._failed_session_id,
                "refund_ticket:failed-red",
                "REFUND",
                "failed-red",
                "chatflow_sop",
                "refund_ticket",
                input_snapshot={"orderNo": "FAILED-RED"},
                status="FAILED",
            )
            self._failed_task_id = int(failed_task["id"])
            recovered = repository.create_session({"demoSeed": "085", "storyId": "confirmed-retry-recovery"})
            self._recoverable_session_id = int(recovered["id"])
            recoverable_task = repository.upsert_task(
                self._recoverable_session_id,
                "baggage_qa:recoverable-red",
                "QA",
                "recoverable-red",
                "stub_qa",
                "baggage_allowance",
                input_snapshot={"topic": "baggage_allowance"},
                status="FAILED",
            )
            recoverable_task = repository.update_task(
                int(recoverable_task["id"]),
                last_result={
                    "status": "FAILED",
                    "error": {"code": "WORKER_FAILED", "message": "previous deterministic failure"},
                },
            )
            self._recoverable_task_id = int(recoverable_task["id"])
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(runtime_lab_sop_chatflow_ids=None)

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_proposes_and_confirms_retry_cancel_resume_task_controls(self) -> None:
        cases = [
            (self._running_session_id, self._running_task_id, "cancel", "CANCEL_TASK", "CANCELLED"),
            (self._waiting_session_id, self._waiting_task_id, "resume", "RESUME_TASK", "WAITING"),
            (self._failed_session_id, self._failed_task_id, "retry", "RESUME_TASK", "WAITING"),
        ]
        with TestClient(app) as client:
            for session_id, task_id, control_type, command_type, expected_status in cases:
                response = client.post(
                    f"/api/v1/customer-assistant/sessions/{session_id}/tasks/{task_id}/controls/propose",
                    json={"controlType": control_type, "reason": "operator requested"},
                )
                self.assertEqual(response.status_code, 200, response.text)
                action = response.json()["data"]
                self.assertEqual(action["status"], "PENDING")
                self.assertEqual(action["actionType"], "PROPOSED_TASK_COMMAND")
                self.assertEqual(action["payload"]["controlType"], control_type)
                self.assertEqual(action["payload"]["taskCommand"]["type"], command_type)

                confirm = client.post(f"/api/v1/customer-assistant/proposed-actions/{action['id']}/confirm")
                self.assertEqual(confirm.status_code, 200, confirm.text)

                tasks = client.get(f"/api/v1/customer-assistant/sessions/{session_id}/tasks").json()["data"]["list"]
                self.assertEqual(_task_status(tasks, task_id), expected_status)
                events = client.get(f"/api/v1/customer-assistant/sessions/{session_id}/events").json()["data"]["list"]
                event_types = [item["type"] for item in events]
                self.assertIn("task_control_proposed", event_types)
                self.assertIn("proposed_task_command_confirmed", event_types)

    def test_confirmed_retry_dispatches_worker_and_recovers_failed_task(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/customer-assistant/sessions/{self._recoverable_session_id}/tasks/{self._recoverable_task_id}/controls/propose",
                json={"controlType": "retry", "reason": "operator requested fresh worker attempt"},
            )
            self.assertEqual(response.status_code, 200, response.text)
            action = response.json()["data"]
            self.assertEqual(action["status"], "PENDING")
            self.assertEqual(action["payload"]["taskCommand"]["type"], "RESUME_TASK")

            confirm = client.post(f"/api/v1/customer-assistant/proposed-actions/{action['id']}/confirm")
            self.assertEqual(confirm.status_code, 200, confirm.text)
            confirmed = confirm.json()["data"]
            self.assertEqual(confirmed["status"], "CONFIRMED")
            self.assertTrue(confirmed["result"]["applied"])

            tasks = client.get(
                f"/api/v1/customer-assistant/sessions/{self._recoverable_session_id}/tasks"
            ).json()["data"]["list"]
            task = _task_by_id(tasks, self._recoverable_task_id)
            self.assertEqual(task["status"], "COMPLETED")
            self.assertEqual(task["lastResult"]["status"], "COMPLETED")
            self.assertIn("手提行李", task["lastResult"]["customerReplyDraft"])
            refs = task["workerAsyncRefs"]
            self.assertTrue(refs["supported"])
            self.assertTrue(str(refs["workerRunId"]).startswith("customer-assistant-worker-run-"))

            worker_run = client.get(refs["workerStatusRef"]).json()["data"]
            self.assertEqual(worker_run["status"], "COMPLETED")

            events = client.get(
                f"/api/v1/customer-assistant/sessions/{self._recoverable_session_id}/events"
            ).json()["data"]["list"]
            event_types = [item["type"] for item in events]
            self.assertIn("task_control_proposed", event_types)
            self.assertIn("proposed_task_command_confirmed", event_types)
            self.assertIn("task_started", event_types)
            self.assertIn("worker_started", event_types)
            self.assertIn("task_completed", event_types)

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session


def _task_status(tasks: list[dict[str, object]], task_id: int) -> str:
    for task in tasks:
        if int(task["id"]) == task_id:
            return str(task["status"])
    raise AssertionError(f"Task not found: {task_id}")


def _task_by_id(tasks: list[dict[str, object]], task_id: int) -> dict[str, object]:
    for task in tasks:
        if int(task["id"]) == task_id:
            return task
    raise AssertionError(f"Task not found: {task_id}")
