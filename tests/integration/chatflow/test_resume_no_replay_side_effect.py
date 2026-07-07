import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class ChatflowResumeNoReplaySideEffectTest(unittest.TestCase):
    def test_resume_only_restores_waiting_node_and_does_not_replay_completed_side_effect(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_side_effect_then_question_chatflow(client, stamp)
            started = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={
                    "input": {
                        "sys.query": "need confirmation",
                        "sys.conversation_id": f"side-effect-replay-{stamp}",
                    }
                },
            ).json()["data"]
            interrupted = _wait_for_result(client, started["resultRef"], "INTERRUPTED")
            before_resume_nodes = client.get(started["nodesRef"]).json()["data"]["list"]

            resumed_response = client.post(
                f"/api/v1/runtime-runs/{started['runId']}/resume",
                json={"resumeData": {"answer": "yes"}, "idempotencyKey": f"side-effect-replay-{stamp}"},
            )
            after_resume_nodes = client.get(started["nodesRef"]).json()["data"]["list"]

        self.assertEqual(interrupted["waitingNodeKeys"], ["question_1"])
        self.assertEqual(
            [(node["nodeKey"], node["status"]) for node in interrupted["waitingNodes"]],
            [("question_1", "WAITING")],
        )
        self.assertEqual(_node_run_count(before_resume_nodes, "notify_1"), 1)
        self.assertEqual(_node_run_count(after_resume_nodes, "notify_1"), 1)
        notify_node = next(node for node in after_resume_nodes if node["nodeKey"] == "notify_1")
        self.assertEqual(notify_node["outputs"]["sideEffect"], f"sent-{stamp}")
        self.assertEqual(resumed_response.status_code, 200, resumed_response.text)
        resumed = resumed_response.json()["data"]
        self.assertEqual(resumed["status"], "SUCCEEDED")
        self.assertEqual(resumed["waitingNodeKeys"], [])
        self.assertEqual(resumed["waitingNodes"], [])
        self.assertEqual(resumed["output"], {"final": f"answer=yes effect=sent-{stamp}"})


def _wait_for_result(
    client: TestClient,
    result_ref: str,
    wanted_status: str,
    timeout: float = 5.0,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        latest = client.get(result_ref).json()["data"]
        if latest["status"] == wanted_status:
            return latest
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for {wanted_status}; latest={latest}")


def _node_run_count(nodes: list[dict[str, object]], node_key: str) -> int:
    return sum(1 for node in nodes if node["nodeKey"] == node_key)


def _create_side_effect_then_question_chatflow(client: TestClient, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Resume No Replay Side Effect {stamp}",
            "description": "fan-out side effect plus waiting question fixture",
            "nodes": [
                {
                    "nodeKey": "start",
                    "type": "START",
                    "name": "Start",
                    "config": {"ports": [{"key": "default", "allowFanOut": True}]},
                },
                {
                    "nodeKey": "notify_1",
                    "type": "CODE",
                    "name": "Notify",
                    "config": {
                        "language": "python",
                        "code": f"result = {{'sideEffect': 'sent-{stamp}'}}",
                        "outputParameters": [{"name": "sideEffect", "type": "string"}],
                    },
                },
                {
                    "nodeKey": "question_1",
                    "type": "QUESTION",
                    "name": "Confirm",
                    "config": {
                        "question": "确认继续？",
                        "answerType": "text",
                        "outputVariable": "answer",
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {
                        "outputVariable": "final",
                        "output": "answer={{question_1.answer}} effect={{notify_1.sideEffect}}",
                    },
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "notify_1", "condition": None},
                {"sourceNodeKey": "start", "targetNodeKey": "question_1", "condition": None},
                {"sourceNodeKey": "notify_1", "targetNodeKey": "end", "condition": None},
                {"sourceNodeKey": "question_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]
