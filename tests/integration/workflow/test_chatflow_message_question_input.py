import unittest
from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app


class ChatflowMessageQuestionHumanInputTest(unittest.TestCase):
    def test_message_node_emits_message_events_and_continues(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_message_chatflow(client)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={"input": {"sys.query": "Ada"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"], {"final": "sent: Hello Ada"})

    def test_selected_message_node_returns_streaming_event_contract(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_message_chatflow(client)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/nodes/message_1/runs",
                json={"input": {"sys.query": "Ada"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        events = response.json()["data"]["output"]["events"]
        self.assertEqual([event["type"] for event in events], ["message_delta", "message_done"])

    def test_question_node_interrupts_then_resumes_same_graph_from_answer(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_question_chatflow(client)
            interrupted = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={"input": {"sys.query": "start"}},
            )
            resumed = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={"input": {"sys.query": "start", "resume": {"question_1": {"answer": "yes"}}}},
            )

        self.assertEqual(interrupted.status_code, 200, interrupted.text)
        self.assertEqual(interrupted.json()["data"]["status"], "INTERRUPTED")
        self.assertEqual(interrupted.json()["data"]["output"]["interrupt"]["nodeKey"], "question_1")
        self.assertEqual(resumed.status_code, 200, resumed.text)
        self.assertEqual(resumed.json()["data"]["output"], {"final": "answer=yes"})

    def test_human_input_node_uses_resume_payload_and_continues(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_human_input_chatflow(client)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={"input": {"resume": {"human_input_1": {"payload": {"approved": True, "note": "ok"}}}}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["data"]["status"], "SUCCEEDED")
        self.assertEqual(response.json()["data"]["output"], {"final": "approved=True note=ok"})


def _create_message_chatflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Message Chatflow {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "message_1",
                    "type": "MESSAGE",
                    "name": "消息",
                    "config": {
                        "content": "Hello {{start.sys.query}}",
                        "outputVariable": "content",
                        "streamOutput": "enabled",
                    },
                },
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final", "output": "sent: {{message_1.content}}"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "message_1", "condition": None},
                {"sourceNodeKey": "message_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_question_chatflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Question Chatflow {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "question_1",
                    "type": "QUESTION",
                    "name": "问题",
                    "config": {"question": "继续吗？", "outputVariable": "answer", "answerType": "text"},
                },
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


def _create_human_input_chatflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Human Input Chatflow {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "human_input_1",
                    "type": "HUMAN_INPUT",
                    "name": "人工输入",
                    "config": {"prompt": "请审核", "outputVariable": "payload"},
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {
                        "outputVariable": "final",
                        "output": "approved={{human_input_1.approved}} note={{human_input_1.note}}",
                    },
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "human_input_1", "condition": None},
                {"sourceNodeKey": "human_input_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
