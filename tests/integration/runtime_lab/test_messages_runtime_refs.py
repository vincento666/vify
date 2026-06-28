"""Spec 213.3.2 contract — /messages envelope exposes chatflowSession refs.

POST ``/messages`` and ``/sessions/{id}/messages`` must include a
``chatflowSession`` block on the active task envelope, sourced from the
first-class chatflow ref columns added in slice 213.3.1.
"""

import unittest

from fastapi.testclient import TestClient

from app.core.database import get_session_factory
from app.main import app
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository


class RuntimeLabMessagesChatflowSessionRefsTest(unittest.TestCase):
    def test_sessions_messages_envelope_includes_chatflow_session_refs(self) -> None:
        runtime_session_id, task_id = _seed_session_with_chatflow_task()

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/runtime-lab/sessions/{runtime_session_id}/messages",
                json={"message": "继续走下一步", "idempotencyKey": f"chatflow-refs-{task_id}"},
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        active_task = payload.get("activeTask")
        self.assertIsNotNone(active_task)
        chatflow_session = active_task.get("chatflowSession")
        self.assertIsNotNone(
            chatflow_session,
            f"expected chatflowSession on activeTask, got {active_task!r}",
        )
        self.assertEqual(chatflow_session["chatflowId"], 4242)
        self.assertEqual(chatflow_session["sessionId"], 7777)
        self.assertEqual(chatflow_session["runId"], 9001)
        self.assertEqual(chatflow_session["eventId"], 12345)
        self.assertEqual(chatflow_session["checkpointId"], 9999)
        self.assertEqual(chatflow_session["runtimeVersion"], "v2")
        self.assertEqual(chatflow_session["statusRef"], "/api/v1/runtime-runs/9001")
        self.assertEqual(chatflow_session["eventsRef"], "/api/v1/runtime-runs/9001/events")
        self.assertEqual(
            chatflow_session["eventStreamRef"],
            "/api/v1/runtime-runs/9001/events/stream?afterSequence=0",
        )
        self.assertEqual(chatflow_session["nodesRef"], "/api/v1/runtime-runs/9001/nodes")
        self.assertEqual(chatflow_session["resultRef"], "/api/v1/runtime-runs/9001/result")
        # Back-compat: legacy fields still present alongside the new block.
        self.assertIn("currentStep", active_task)
        self.assertIn("businessRefs", active_task)

    def test_messages_envelope_includes_chatflow_session_refs(self) -> None:
        # POST /messages (no session_id) bootstraps a fresh session; the SOP
        # arbitrator routes "我要退票" through the chatflow adapter, which writes
        # __chatflow into scoped_variables. After slice 213.3.1 those refs are
        # promoted to first-class columns; slice 213.3.2 must surface them on
        # the envelope.
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/runtime-lab/messages",
                json={"message": "我要退票", "idempotencyKey": "bootstrap-chatflow-refs"},
            )

        self.assertEqual(response.status_code, 200, response.text)
        active_task = response.json()["data"].get("activeTask")
        self.assertIsNotNone(active_task)
        chatflow_session = active_task.get("chatflowSession")
        self.assertIsNotNone(
            chatflow_session,
            f"expected chatflowSession on activeTask, got {active_task!r}",
        )
        run_id = chatflow_session["runId"]
        self.assertIsInstance(run_id, int)
        self.assertGreater(run_id, 0)
        self.assertEqual(chatflow_session["statusRef"], f"/api/v1/runtime-runs/{run_id}")
        self.assertEqual(chatflow_session["eventsRef"], f"/api/v1/runtime-runs/{run_id}/events")
        self.assertEqual(
            chatflow_session["eventStreamRef"],
            f"/api/v1/runtime-runs/{run_id}/events/stream?afterSequence=0",
        )
        self.assertEqual(chatflow_session["nodesRef"], f"/api/v1/runtime-runs/{run_id}/nodes")
        self.assertEqual(chatflow_session["resultRef"], f"/api/v1/runtime-runs/{run_id}/result")
        self.assertEqual(chatflow_session["runtimeVersion"], "v2")
        # Back-compat: legacy fields still present alongside the new block.
        self.assertIn("currentStep", active_task)
        self.assertIn("businessRefs", active_task)


def _seed_session_with_chatflow_task() -> tuple[int, int]:
    with get_session_factory()() as session:
        repository = RuntimeLabRepository(session)
        runtime_session = repository.create_session()
        runtime_session_id = int(runtime_session["id"])
        task = repository.create_task(
            runtime_session_id,
            sop_id="refund_ticket",
            current_step="collect_order_no",
            business_refs={"route": "BJ-SH"},
            chatflow_id=4242,
            chatflow_session_id=7777,
            chatflow_run_id=9001,
            chatflow_event_id=12345,
            chatflow_checkpoint_id=9999,
            runtime_version="v2",
        )
        checkpoint = repository.create_checkpoint(
            runtime_session_id,
            int(task["id"]),
            sop_id="refund_ticket",
            current_step="collect_order_no",
            pending_prompt="请提供订单号",
            collected={"route": "BJ-SH"},
            scoped_variables={
                "__chatflow": {
                    "chatflowId": 4242,
                    "sessionId": "7777",
                    "runId": 9001,
                    "eventId": 12345,
                    "checkpointId": 9999,
                    "runtimeVersion": 2,
                },
            },
        )
        repository.update_task_state(
            int(task["id"]),
            status="RUNNING",
            current_step="collect_order_no",
            checkpoint_id=int(checkpoint["id"]),
            business_refs={"route": "BJ-SH"},
        )
        return runtime_session_id, int(task["id"])


if __name__ == "__main__":
    unittest.main()
