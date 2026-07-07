import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import get_session_factory
from app.main import app
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.repository import WorkflowRepository


class RuntimeLabChildChatflowAggregationContractTest(unittest.TestCase):
    def test_trace_aggregates_execution_facts_from_child_chatflow_only(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_trace_chatflow(client, stamp)
            runtime_session_id = _seed_runtime_lab_task_with_child_runtime(
                chatflow_id=int(chatflow["id"]),
                stamp=stamp,
            )

            response = client.get(f"/api/v1/runtime-lab/sessions/{runtime_session_id}/chatflow-trace")

        self.assertEqual(response.status_code, 200, response.text)
        trace = response.json()["data"]
        self.assertEqual(trace["total"], 1)
        task = trace["tasks"][0]

        self.assertEqual(task["currentStep"], "question_1")
        self.assertEqual(task["pendingPrompt"], "请确认是否继续？")
        self.assertEqual(task["runStatus"], "INTERRUPTED")
        self.assertEqual(task["checkpoint"]["pendingNodeKey"], "question_1")
        self.assertEqual(task["checkpoint"]["resumeSchema"]["answerType"], "text")
        self.assertEqual(task["variables"]["collected"]["order_no"], "TK-2163")
        self.assertEqual(task["variables"]["scopedVariables"]["conversation.order_no"], "TK-2163")
        self.assertEqual(
            [(event["type"], event["nodeKey"]) for event in task["nodeEvents"]],
            [
                ("workflow_run_started", ""),
                ("interrupt", "question_1"),
            ],
        )

        runtime_lab_events = {event["eventType"]: event["payload"] for event in task["ledgerEvents"]}
        self.assertIn("TASK_STARTED", runtime_lab_events)
        self.assertNotIn("currentStep", runtime_lab_events["TASK_STARTED"])


def _create_trace_chatflow(client: TestClient, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"216.3 trace contract {stamp}",
            "description": "runtime-lab child aggregation contract fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "question_1",
                    "type": "QUESTION",
                    "name": "Confirm",
                    "config": {"question": "请确认是否继续？", "outputVariable": "answer", "answerType": "text"},
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


def _seed_runtime_lab_task_with_child_runtime(*, chatflow_id: int, stamp: int) -> int:
    chatflow_session_bigint = stamp % 1_000_000_000
    chatflow_session_id = str(chatflow_session_bigint)
    with get_session_factory()() as session:
        workflow_repository = WorkflowRepository(session)
        state_repository = ChatflowStateRepository(session)
        run_id = workflow_repository.create_run(chatflow_id, {"sys.query": "start"})
        workflow_repository.finish_run(
            run_id,
            "INTERRUPTED",
            {"interrupt": {"nodeKey": "question_1", "question": "请确认是否继续？"}},
        )
        state_repository.create_session(
            session_id=chatflow_session_id,
            chatflow_id=chatflow_id,
            conversation_id=f"conversation-{stamp}",
            user_id="runtime-lab",
            channel="runtime-lab",
            channel_id="",
            status="active",
            current_run_id=run_id,
            variables={
                "conversation": {"order_no": "TK-2163"},
                "node_outputs": {"question_1": {"prompt": "请确认是否继续？"}},
            },
        )
        checkpoint = state_repository.create_checkpoint(
            session_id=chatflow_session_id,
            chatflow_id=chatflow_id,
            run_id=run_id,
            pending_node_key="question_1",
            execution_context={"input": {"sys.query": "start"}},
            node_outputs={"collect": {"collected": {"order_no": "TK-2163"}}},
            variable_scopes={"conversation": {"order_no": "TK-2163"}},
            resume_schema={"answerType": "text"},
        )
        state_repository.append_event(
            session_id=chatflow_session_id,
            chatflow_id=chatflow_id,
            run_id=run_id,
            event_type="workflow_run_started",
            payload={"runId": run_id},
        )
        interrupt_event = state_repository.append_event(
            session_id=chatflow_session_id,
            chatflow_id=chatflow_id,
            run_id=run_id,
            event_type="interrupt",
            node_key="question_1",
            payload={"question": "请确认是否继续？"},
            checkpoint_id=int(checkpoint["id"]),
        )
        state_repository.link_checkpoint_event(int(checkpoint["id"]), int(interrupt_event["id"]))

        repository = RuntimeLabRepository(session)
        runtime_session = repository.create_session()
        runtime_session_id = int(runtime_session["id"])
        task = repository.create_task(
            runtime_session_id,
            sop_id="refund_ticket",
            chatflow_id=chatflow_id,
            chatflow_session_id=chatflow_session_bigint,
            chatflow_run_id=run_id,
            chatflow_event_id=int(interrupt_event["id"]),
            chatflow_checkpoint_id=int(checkpoint["id"]),
            runtime_version="v2",
        )
        repository.append_event(
            runtime_session_id,
            "TASK_STARTED",
            {"taskId": task["id"], "sopId": "refund_ticket", "currentStep": "stale_router_copy"},
        )
        return runtime_session_id


if __name__ == "__main__":
    unittest.main()
