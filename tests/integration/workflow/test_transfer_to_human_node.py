import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class TransferToHumanNodeIntegrationTest(unittest.TestCase):
    def test_chatflow_transfer_to_human_creates_ticket_and_handoff_session(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_transfer_chatflow(client, stamp)
            run = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={
                    "input": {
                        "sys.query": "我要人工",
                        "sys.conversation_id": f"handoff-{stamp}",
                        "sys.user_id": "user-0191",
                        "sys.channel": "web",
                    }
                },
            )
            handoffs = client.get("/api/v1/handoffs")
            session = client.get(f"/api/v1/chatflows/{chatflow['id']}/sessions/handoff-{stamp}")

        self.assertEqual(run.status_code, 200, run.text)
        data = run.json()["data"]
        self.assertEqual(data["status"], "INTERRUPTED")
        self.assertEqual(data["sessionStatus"], "handoff")
        self.assertEqual(data["output"]["handoff_status"], "queued")
        self.assertEqual(data["output"]["queue"], "vip-support")
        self.assertGreater(int(data["output"]["handoff_id"]), 0)
        self.assertIn("handoff_requested", [event["type"] for event in data["events"]])

        self.assertEqual(handoffs.status_code, 200, handoffs.text)
        tickets = handoffs.json()["data"]["list"]
        ticket = next(item for item in tickets if item["id"] == int(data["output"]["handoff_id"]))
        self.assertEqual(ticket["sessionId"], f"handoff-{stamp}")
        self.assertEqual(ticket["status"], "queued")
        self.assertEqual(ticket["queue"], "vip-support")
        self.assertEqual(ticket["priority"], "high")

        self.assertEqual(session.status_code, 200, session.text)
        self.assertEqual(session.json()["data"]["status"], "handoff")

    def test_transfer_to_human_is_chatflow_only(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            workflow = _create_transfer_workflow(client, stamp)
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"userMessage": "help"}},
            )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("Chatflow", response.text)


def _create_transfer_chatflow(client: TestClient, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"019.1 Handoff {stamp}",
            "description": "transfer to human fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "handoff_1",
                    "type": "TRANSFER_TO_HUMAN",
                    "name": "转人工",
                    "config": {
                        "message": "已为你转接人工客服，请稍候。",
                        "queue": "vip-support",
                        "reason": "user_request",
                        "priority": "high",
                        "slaMinutes": 30,
                    },
                },
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final", "output": "done"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "handoff_1", "condition": None},
                {"sourceNodeKey": "handoff_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_transfer_workflow(client: TestClient, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"019.1 Workflow Handoff {stamp}",
            "description": "workflow transfer fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {"nodeKey": "handoff_1", "type": "TRANSFER_TO_HUMAN", "name": "转人工", "config": {"queue": "support"}},
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final", "output": "done"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "handoff_1", "condition": None},
                {"sourceNodeKey": "handoff_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
