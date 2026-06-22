import time
import unittest

from fastapi.testclient import TestClient
import sqlalchemy as sa

from app.core.database import Base, get_session_factory
from app.main import app


class ChatflowSessionStateIntegrationTest(unittest.TestCase):
    def test_question_interrupt_creates_waiting_session_events_and_checkpoint(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_question_chatflow(client, stamp)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-legacy",
                json={
                    "input": {
                        "sys.query": "start",
                        "sys.conversation_id": f"conv-{stamp}",
                        "sys.user_id": "user-018",
                        "sys.channel": "web",
                    }
                },
            )

            self.assertEqual(response.status_code, 200, response.text)
            data = response.json()["data"]
            session_id = data["sessionId"]
            run_id = data["runId"]
            checkpoint_id = data["checkpointId"]

            session_response = client.get(f"/api/v1/chatflows/{chatflow['id']}/sessions/{session_id}")
            events_response = client.get(f"/api/v1/chatflows/{chatflow['id']}/runs/{run_id}/events")

        self.assertEqual(data["status"], "INTERRUPTED")
        self.assertEqual(data["sessionStatus"], "waiting")
        self.assertGreater(checkpoint_id, 0)
        self.assertEqual([event["type"] for event in data["events"]], ["message", "interrupt"])

        self.assertEqual(session_response.status_code, 200, session_response.text)
        session_data = session_response.json()["data"]
        self.assertEqual(session_data["status"], "waiting")
        self.assertEqual(session_data["currentRunId"], run_id)
        self.assertEqual(session_data["waitingEvent"]["type"], "interrupt")
        self.assertEqual(session_data["waitingEvent"]["payload"]["nodeKey"], "question_1")
        self.assertEqual(session_data["checkpoint"]["id"], checkpoint_id)
        self.assertEqual(session_data["checkpoint"]["pendingNodeKey"], "question_1")

        self.assertEqual(events_response.status_code, 200, events_response.text)
        events = events_response.json()["data"]["list"]
        self.assertEqual([event["type"] for event in events], ["message", "interrupt"])
        self.assertEqual(events[-1]["checkpointId"], checkpoint_id)
        self.assertEqual(_checkpoint_pending_node(checkpoint_id), "question_1")

    def test_message_chatflow_records_message_and_done_events_for_completed_session(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_message_chatflow(client, stamp)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-legacy",
                json={
                    "input": {
                        "sys.query": "Ada",
                        "sys.conversation_id": f"conv-{stamp}",
                        "sys.user_id": "user-018",
                        "sys.channel": "web",
                    }
                },
            )
            self.assertEqual(response.status_code, 200, response.text)
            data = response.json()["data"]
            events_response = client.get(f"/api/v1/chatflows/{chatflow['id']}/runs/{data['runId']}/events")
            session_response = client.get(f"/api/v1/chatflows/{chatflow['id']}/sessions/{data['sessionId']}")

        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["sessionStatus"], "completed")
        self.assertEqual([event["type"] for event in data["events"]], ["message", "done"])
        self.assertEqual(events_response.status_code, 200, events_response.text)
        self.assertEqual([event["type"] for event in events_response.json()["data"]["list"]], ["message", "done"])
        self.assertEqual(session_response.status_code, 200, session_response.text)
        self.assertEqual(session_response.json()["data"]["status"], "completed")
        self.assertIsNone(session_response.json()["data"]["waitingEvent"])


def _create_question_chatflow(client: TestClient, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"018.1 Question {stamp}",
            "description": "session state question fixture",
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


def _create_message_chatflow(client: TestClient, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"018.1 Message {stamp}",
            "description": "session state message fixture",
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


def _checkpoint_pending_node(checkpoint_id: int) -> str:
    checkpoint_table = Base.metadata.tables["chatflow_checkpoint"]
    with get_session_factory()() as session:
        return str(
            session.execute(
                sa.select(checkpoint_table.c.pending_node_key).where(checkpoint_table.c.id == checkpoint_id)
            ).scalar_one()
        )


if __name__ == "__main__":
    unittest.main()
