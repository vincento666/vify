import time
import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.core.database import get_session_factory


class RuntimeLabChatflowTraceApiTest(unittest.TestCase):
    def test_trace_exposes_bound_chatflow_nodes_variables_events_and_debug_link(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_question_chatflow(client, stamp)
            run_response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={
                    "input": {
                        "sys.query": "start",
                        "sys.conversation_id": f"runtime-trace-{stamp}",
                        "sys.channel": "runtime-lab",
                    }
                },
            )
            self.assertEqual(run_response.status_code, 200, run_response.text)
            run = run_response.json()["data"]
            runtime_session_id = _runtime_session_with_chatflow_checkpoint(
                sop_id="flight_booking",
                chatflow_id=int(chatflow["id"]),
                chatflow_session_id=str(run["sessionId"]),
                run_id=int(run["runId"]),
                event_id=int(run["events"][-1]["id"]),
                checkpoint_id=int(run["checkpointId"]),
            )

            trace_response = client.get(f"/api/v1/runtime-lab/sessions/{runtime_session_id}/chatflow-trace")

        self.assertEqual(trace_response.status_code, 200, trace_response.text)
        trace = trace_response.json()["data"]
        self.assertEqual(trace["total"], 1)
        task_trace = trace["tasks"][0]
        self.assertEqual(task_trace["sopId"], "flight_booking")
        self.assertEqual(task_trace["chatflow"]["chatflowId"], chatflow["id"])
        self.assertEqual(task_trace["chatflow"]["canvasPath"], f"/chatflows/{chatflow['id']}/canvas")
        self.assertEqual(
            task_trace["chatflow"]["debugPath"],
            f"/chatflows/{chatflow['id']}/canvas?runId={run['runId']}&debug=1",
        )
        self.assertTrue(any(node["nodeKey"] == "question_1" and node["current"] for node in task_trace["nodes"]))
        question_node = next(node for node in task_trace["nodes"] if node["nodeKey"] == "question_1")
        self.assertEqual(question_node["usage"]["totalTokens"], 0)
        self.assertEqual(question_node["inputs"]["rendered"]["question"], "继续吗？")
        self.assertEqual(question_node["inputs"]["runtimeInput"]["sys.query"], "start")
        self.assertIn("question_1", [event["nodeKey"] for event in task_trace["events"]])
        self.assertEqual(task_trace["variables"]["collected"]["route"], "北京到上海")
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


def _runtime_session_with_chatflow_checkpoint(
    *,
    sop_id: str,
    chatflow_id: int,
    chatflow_session_id: str,
    run_id: int,
    event_id: int,
    checkpoint_id: int,
) -> int:
    with get_session_factory()() as session:
        repository = RuntimeLabRepository(session)
        runtime_session = repository.create_session()
        runtime_session_id = int(runtime_session["id"])
        task = repository.create_task(
            runtime_session_id,
            sop_id=sop_id,
            current_step="question_1",
            business_refs={"route": "北京到上海"},
        )
        checkpoint = repository.create_checkpoint(
            runtime_session_id,
            int(task["id"]),
            sop_id=sop_id,
            current_step="question_1",
            pending_prompt="继续吗？",
            collected={"route": "北京到上海"},
            scoped_variables={
                "conversation.route": "北京到上海",
                "__chatflow": {
                    "chatflowId": chatflow_id,
                    "runId": run_id,
                    "eventId": event_id,
                    "checkpointId": checkpoint_id,
                    "sessionId": chatflow_session_id,
                    "resumeMode": "event",
                    "collectedNodeIds": [],
                },
            },
        )
        repository.update_task_state(
            int(task["id"]),
            status="RUNNING",
            current_step="question_1",
            checkpoint_id=int(checkpoint["id"]),
            business_refs={"route": "北京到上海"},
        )
        return runtime_session_id


if __name__ == "__main__":
    unittest.main()
