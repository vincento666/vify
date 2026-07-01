"""Spec 213.3.5f contract — chatflow-trace sources from task refs + aggregator.

After slice 213.3.5e banned the SOP-Router DB mirror writes
(``checkpoint.collected`` / ``checkpoint.current_step`` /
``task.business_refs``), the chatflow-trace API must no longer read those
columns. Instead:

- chatflow meta (chatflowId / runId / runtime refs) comes from the task's
  first-class ``chatflow_*`` ref columns (slice 213.3.1).
- ``currentStep`` comes from the durable runtime-v2 waiting checkpoint
  (``pending_node_key``), not the banned ``checkpoint.current_step``.
- ``collected`` / ``businessRefs`` come from the business-context aggregator
  projection (chatflow ``conversation`` scope), not ``checkpoint.collected``.
"""

import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import get_session_factory
from app.main import app
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository


class RuntimeLabChatflowTraceApiTest(unittest.TestCase):
    def test_trace_sources_meta_current_step_and_collected_without_banned_columns(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_question_chatflow(client, stamp)
            chatflow_id = int(chatflow["id"])
            runtime_session_id, run_id = _seed_runtime_session_from_task_refs(
                chatflow_id=chatflow_id,
                stamp=stamp,
            )

            trace_response = client.get(
                f"/api/v1/runtime-lab/sessions/{runtime_session_id}/chatflow-trace"
            )

        self.assertEqual(trace_response.status_code, 200, trace_response.text)
        trace = trace_response.json()["data"]
        self.assertEqual(trace["total"], 1)
        task_trace = trace["tasks"][0]

        # chatflow meta from task ref columns
        self.assertEqual(task_trace["sopId"], "flight_booking")
        self.assertEqual(task_trace["chatflow"]["chatflowId"], chatflow_id)
        self.assertEqual(task_trace["chatflow"]["runId"], run_id)
        self.assertEqual(task_trace["chatflow"]["canvasPath"], f"/chatflows/{chatflow_id}/canvas")
        self.assertEqual(
            task_trace["chatflow"]["debugPath"],
            f"/chatflows/{chatflow_id}/canvas?runId={run_id}&debug=1",
        )
        self.assertEqual(task_trace["chatflow"]["statusRef"], f"/api/v1/runtime-runs/{run_id}")
        self.assertEqual(
            task_trace["chatflow"]["eventStreamRef"],
            f"/api/v1/runtime-runs/{run_id}/events/stream?afterSequence=0",
        )

        # current step from durable runtime-v2 waiting checkpoint
        self.assertEqual(task_trace["currentStep"], "question_1")
        self.assertTrue(
            any(node["nodeKey"] == "question_1" and node["current"] for node in task_trace["nodes"])
        )

        # collected / businessRefs from aggregator (chatflow conversation scope)
        self.assertEqual(task_trace["variables"]["collected"]["route"], "北京到上海")
        self.assertEqual(task_trace["variables"]["businessRefs"]["route"], "北京到上海")
        self.assertIn("node_outputs", task_trace["variables"]["session"])


def _create_question_chatflow(client: TestClient, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Runtime trace question {stamp}",
            "description": "runtime-lab trace fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "question_1",
                    "type": "QUESTION",
                    "name": "确认问题",
                    "config": {"question": "继续吗？", "outputVariable": "answer", "answerType": "text"},
                },
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final", "output": "ok"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "question_1", "condition": None},
                {"sourceNodeKey": "question_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _seed_runtime_session_from_task_refs(*, chatflow_id: int, stamp: int) -> tuple[int, int]:
    chatflow_session_bigint = stamp % 1_000_000_000
    chatflow_session_id = str(chatflow_session_bigint)
    run_id = stamp % 2_000_000_000
    with get_session_factory()() as session:
        state_repository = ChatflowStateRepository(session)
        state_repository.create_session(
            session_id=chatflow_session_id,
            chatflow_id=chatflow_id,
            conversation_id=chatflow_session_id,
            user_id="runtime-lab",
            channel="runtime-lab",
            channel_id="",
            status="active",
            current_run_id=run_id,
            variables={
                "conversation": {"route": "北京到上海"},
                "node_outputs": {"question_1": {"answer": "ok"}},
            },
        )
        checkpoint = state_repository.create_checkpoint(
            session_id=chatflow_session_id,
            chatflow_id=chatflow_id,
            run_id=run_id,
            pending_node_key="question_1",
            execution_context={},
            node_outputs={},
            variable_scopes={},
            resume_schema={},
        )

        repository = RuntimeLabRepository(session)
        runtime_session = repository.create_session()
        runtime_session_id = int(runtime_session["id"])
        repository.create_task(
            runtime_session_id,
            sop_id="flight_booking",
            chatflow_id=chatflow_id,
            chatflow_session_id=chatflow_session_bigint,
            chatflow_run_id=run_id,
            chatflow_checkpoint_id=int(checkpoint["id"]),
            runtime_version="v2",
        )
        return runtime_session_id, run_id


if __name__ == "__main__":
    unittest.main()
