import unittest

from app.modules.runtime_lab.domain.payload import format_turn
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables
from tests.support.mysql import mysql8_session


class RuntimeLabNoStateMirroringIntegrationTest(unittest.TestCase):
    def test_task_payload_and_event_ledger_do_not_mirror_child_execution_state(self) -> None:
        with mysql8_session("runtime_lab_no_state_mirroring", register=register_runtime_lab_tables) as session:
            repository = RuntimeLabRepository(session)
            service = RuntimeLabService(repository)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            turn = service.handle_message(session_id, "我要退票")
            payload = format_turn(turn)
            task_rows = repository.list_tasks(session_id)
            events = repository.list_events(session_id)

        forbidden_public_task_keys = {
            "currentStep",
            "pendingPrompt",
            "collected",
            "scopedVariables",
            "checkpoint",
            "checkpointId",
            "nodeEvents",
            "runStatus",
            "businessRefs",
        }
        active_task = payload["activeTask"]
        self.assertIsNotNone(active_task)
        assert active_task is not None
        self.assertTrue(forbidden_public_task_keys.isdisjoint(active_task))
        self.assertIn("chatflowSession", active_task)

        forbidden_ledger_columns = {
            "current_step",
            "pending_prompt",
            "collected",
            "scoped_variables",
            "checkpoint_id",
            "node_events",
            "run_status",
            "business_refs",
        }
        self.assertEqual(len(task_rows), 1)
        self.assertTrue(forbidden_ledger_columns.isdisjoint(task_rows[0]))

        forbidden_event_keys = {
            "currentStep",
            "pendingPrompt",
            "collected",
            "scopedVariables",
            "checkpoint",
            "checkpointId",
            "nodeEvents",
            "runStatus",
            "businessRefs",
        }
        for event in events:
            with self.subTest(event=event["event_type"]):
                payload = event.get("payload") or {}
                self.assertTrue(forbidden_event_keys.isdisjoint(payload))


if __name__ == "__main__":
    unittest.main()
