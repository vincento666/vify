import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class ChatflowSessionGatewayApiContractTest(unittest.TestCase):
    def test_message_creates_session_and_returns_answer_when_omitted(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_message_chatflow(client, "contract-omitted")
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/messages",
                json={
                    "message": "Ada",
                    "userId": "user-contract",
                    "channel": "web",
                    "waitTimeoutMs": 1200,
                    "idempotencyKey": f"contract-omitted-{time.time_ns()}",
                },
            )

            self.assertEqual(response.status_code, 200, response.text)
            data = response.json()["data"]
            session_response = client.get(f"/api/v1/chatflows/{chatflow['id']}/sessions/{data['sessionId']}")

        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["answer"], "sent: Hello Ada")
        self.assertTrue(data["sessionId"])
        self.assertEqual(data["conversationId"], data["sessionId"])
        self.assertGreater(data["runId"], 0)
        self.assertIn("/api/v1/runtime-runs/", data["eventsRef"])
        self.assertIn("/api/v1/runtime-runs/", data["resultRef"])
        self.assertEqual(session_response.status_code, 200, session_response.text)
        self.assertEqual(session_response.json()["data"]["sessionId"], data["sessionId"])

    def test_message_idempotency_key_replays_same_run(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_message_chatflow(client, "contract-idempotency")
            first = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/messages",
                json={"message": "Grace", "waitTimeoutMs": 1200, "idempotencyKey": f"same-turn-{stamp}"},
            )
            self.assertEqual(first.status_code, 200, first.text)
            first_data = first.json()["data"]
            second = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/messages",
                json={
                    "message": "Grace",
                    "sessionId": first_data["sessionId"],
                    "waitTimeoutMs": 1200,
                    "idempotencyKey": f"same-turn-{stamp}",
                },
            )
            events = client.get(f"/api/v1/chatflows/{chatflow['id']}/runs/{first_data['runId']}/events").json()[
                "data"
            ]["list"]

        self.assertEqual(second.status_code, 200, second.text)
        second_data = second.json()["data"]
        self.assertEqual(second_data["runId"], first_data["runId"])
        self.assertTrue(second_data["idempotentReplay"])
        self.assertEqual([event["type"] for event in events].count("workflow_run_started"), 1)

    def test_message_without_wait_returns_runtime_refs_for_running_turn(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_message_chatflow(client, "contract-running")
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/messages",
                json={"message": "Linus", "waitTimeoutMs": 0, "idempotencyKey": f"running-{time.time_ns()}"},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "RUNNING")
        self.assertIsNone(data["answer"])
        self.assertIn(f"/api/v1/runtime-runs/{data['runId']}", data["statusRef"])
        self.assertIn(f"/api/v1/runtime-runs/{data['runId']}/events", data["eventsRef"])
        self.assertIn(f"/api/v1/runtime-runs/{data['runId']}/result", data["resultRef"])


def _create_message_chatflow(client: TestClient, label: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"196.1 {label} {time.time_ns()}",
            "description": "chatflow session gateway contract fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "message_1",
                    "type": "MESSAGE",
                    "name": "Message",
                    "config": {"content": "Hello {{start.sys.query}}", "outputVariable": "content"},
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "sent: {{message_1.content}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "message_1", "condition": None},
                {"sourceNodeKey": "message_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
