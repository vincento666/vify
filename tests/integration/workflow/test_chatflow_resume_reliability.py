from datetime import datetime, timedelta
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory
from app.main import app


class ChatflowResumeReliabilityIntegrationTest(unittest.TestCase):
    def test_idempotency_key_replays_completed_resume_result(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_question_chatflow(client, stamp)
            interrupted = _start(client, int(chatflow["id"]), stamp)
            run_id = int(interrupted["runId"])
            event_id = int(interrupted["events"][-1]["id"])
            first = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs/{run_id}/resume",
                json={"eventId": event_id, "resumeData": {"answer": "refund"}, "idempotencyKey": "idem-0185"},
            )
            replay = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs/{run_id}/resume",
                json={"eventId": event_id, "resumeData": {"answer": "refund"}, "idempotencyKey": "idem-0185"},
            )

        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertEqual(replay.json()["data"]["runId"], run_id)
        self.assertEqual(replay.json()["data"]["status"], "SUCCEEDED")
        self.assertEqual(replay.json()["data"]["output"], first.json()["data"]["output"])

    def test_resume_rejects_expired_checkpoint(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_question_chatflow(client, stamp)
            interrupted = _start(client, int(chatflow["id"]), stamp)
            _expire_checkpoint(int(interrupted["checkpointId"]))
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs/{interrupted['runId']}/resume",
                json={"eventId": interrupted["events"][-1]["id"], "resumeData": {"answer": "refund"}},
            )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("expired", response.text.lower())

    def test_resume_rejects_wrong_event_id(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_question_chatflow(client, stamp)
            interrupted = _start(client, int(chatflow["id"]), stamp)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs/{interrupted['runId']}/resume",
                json={"eventId": int(interrupted["events"][-1]["id"]) + 1000, "resumeData": {"answer": "refund"}},
            )

        self.assertEqual(response.status_code, 404, response.text)


def _create_question_chatflow(client: TestClient, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"018.5 Reliability {stamp}",
            "description": "resume reliability fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {"nodeKey": "question_1", "type": "QUESTION", "name": "问题", "config": {"question": "主题？", "outputVariable": "answer"}},
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final", "output": "topic={{question_1.answer}}"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "question_1", "condition": None},
                {"sourceNodeKey": "question_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _start(client: TestClient, chatflow_id: int, stamp: int) -> dict[str, object]:
    response = client.post(
        f"/api/v1/chatflows/{chatflow_id}/runs-legacy",
        json={"input": {"sys.query": "start", "sys.conversation_id": f"reliability-{stamp}"}},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["status"] == "INTERRUPTED", data
    return data


def _expire_checkpoint(checkpoint_id: int) -> None:
    checkpoint_table = Base.metadata.tables["chatflow_checkpoint"]
    with get_session_factory()() as session:
        session.execute(
            checkpoint_table.update()
            .where(checkpoint_table.c.id == checkpoint_id)
            .values(expires_at=datetime.now() - timedelta(minutes=1))
        )
        session.commit()


if __name__ == "__main__":
    unittest.main()
