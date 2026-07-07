import unittest

from app.modules.runtime_lab.domain.payload import format_turn
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables
from tests.support.mysql import mysql8_session


class SopRouterAsyncRefsIntegrationTest(unittest.TestCase):
    def test_started_sop_turn_exposes_child_chatflow_refs_without_mirror_fields(self) -> None:
        with mysql8_session("runtime_lab_sop_router_async_refs", register=register_runtime_lab_tables) as session:
            repository = RuntimeLabRepository(session)
            service = RuntimeLabService(repository)
            runtime_session = service.create_session()

            turn = service.handle_message(int(runtime_session["id"]), "我要退票")
            payload = format_turn(turn)
            task_rows = repository.list_tasks(int(runtime_session["id"]))

        active_task = payload["activeTask"]
        self.assertIsNotNone(active_task)
        assert active_task is not None
        self.assertEqual(active_task["sopId"], "refund_ticket")
        self.assertNotIn("currentStep", active_task)
        self.assertNotIn("businessRefs", active_task)

        chatflow_session = active_task.get("chatflowSession")
        self.assertIsNotNone(chatflow_session)
        assert chatflow_session is not None
        run_id = chatflow_session["runId"]
        self.assertGreater(chatflow_session["chatflowId"], 0)
        self.assertGreater(chatflow_session["sessionId"], 0)
        self.assertGreater(run_id, 0)
        self.assertEqual(chatflow_session["statusRef"], f"/api/v1/runtime-runs/{run_id}")
        self.assertEqual(chatflow_session["eventsRef"], f"/api/v1/runtime-runs/{run_id}/events")
        self.assertEqual(
            chatflow_session["eventStreamRef"],
            f"/api/v1/runtime-runs/{run_id}/events/stream?afterSequence=0",
        )
        self.assertEqual(chatflow_session["nodesRef"], f"/api/v1/runtime-runs/{run_id}/nodes")
        self.assertEqual(chatflow_session["resultRef"], f"/api/v1/runtime-runs/{run_id}/result")

        self.assertEqual(len(task_rows), 1)
        self.assertNotIn("current_step", task_rows[0])
        self.assertNotIn("business_refs", task_rows[0])
        self.assertEqual(task_rows[0]["chatflow_run_id"], run_id)


if __name__ == "__main__":
    unittest.main()
