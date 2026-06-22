import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class ChatflowRunDebugDetailTest(unittest.TestCase):
    def test_chatflow_run_debug_detail_includes_session_events_variables_and_nodes(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_question_chatflow(client, stamp)
            interrupted = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-legacy",
                json={
                    "input": {
                        "sys.query": "start warranty flow",
                        "sys.conversation_id": f"conv-0213-{stamp}",
                        "sys.user_id": "user-0213",
                        "sys.channel": "web",
                    }
                },
            ).json()["data"]
            run_id = int(interrupted["runId"])
            event_id = int(interrupted["events"][-1]["id"])
            resumed = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs/{run_id}/resume",
                json={"eventId": event_id, "resumeData": {"answer": "yes"}},
            ).json()["data"]

            response = client.get(f"/api/v1/chatflows/{chatflow['id']}/runs/{run_id}/debug")

        self.assertEqual(resumed["status"], "SUCCEEDED")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["runId"], run_id)
        self.assertEqual(data["ownerType"], "CHATFLOW")
        self.assertEqual(data["ownerId"], chatflow["id"])
        self.assertEqual(data["session"]["sessionId"], interrupted["sessionId"])
        self.assertEqual(data["session"]["conversationId"], f"conv-0213-{stamp}")
        self.assertEqual(data["session"]["userId"], "user-0213")
        self.assertEqual(data["session"]["channel"], "web")
        self.assertIn("sys", data["variables"])
        self.assertEqual([event["type"] for event in data["events"]], ["message", "interrupt", "resume", "done"])
        self.assertIn("streamEvents", data)
        self.assertTrue(any(event["type"] == "message_done" for event in data["streamEvents"]))
        self.assertTrue(any(event["nodeKey"] == "end" and event["content"] == "answer=yes" for event in data["streamEvents"]))
        self.assertTrue(any(node["nodeKey"] == "question_1" for node in data["callTree"]))
        self.assertTrue(any(node["nodeKey"] == "end" for node in data["nodeDetails"]))
        self.assertGreaterEqual(len(data["flamegraph"]), 2)


def _create_question_chatflow(client: TestClient, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"021.3 Question Debug {stamp}",
            "description": "chatflow run debug fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {"nodeKey": "question_1", "type": "QUESTION", "name": "问题", "config": {"question": "继续吗？", "outputVariable": "answer"}},
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final", "output": "answer={{question_1.answer}}"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "question_1", "condition": None},
                {"sourceNodeKey": "question_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
