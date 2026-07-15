import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class ChatflowSessionGatewayIntegrationTest(unittest.TestCase):
    def test_auto_created_session_can_continue_on_second_message(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_echo_chatflow(client, "continue")
            first = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/messages",
                json={"message": "first", "waitTimeoutMs": 1200, "idempotencyKey": f"first-{time.time_ns()}"},
            )
            self.assertEqual(first.status_code, 200, first.text)
            first_data = first.json()["data"]
            second = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/messages",
                json={
                    "message": "second",
                    "sessionId": first_data["sessionId"],
                    "waitTimeoutMs": 1200,
                    "idempotencyKey": f"second-{time.time_ns()}",
                },
            )
            self.assertEqual(second.status_code, 200, second.text)
            second_data = second.json()["data"]
            session = client.get(f"/api/v1/chatflows/{chatflow['id']}/sessions/{first_data['sessionId']}").json()[
                "data"
            ]

        self.assertEqual(second_data["sessionId"], first_data["sessionId"])
        self.assertNotEqual(second_data["runId"], first_data["runId"])
        self.assertEqual(first_data["answer"], "answer:first")
        self.assertEqual(second_data["answer"], "answer:second")
        self.assertEqual(session["currentRunId"], second_data["runId"])
        self.assertEqual(session["status"], "completed")

    def test_session_and_run_events_are_queryable_for_message_turns(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_echo_chatflow(client, "events")
            first = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/messages",
                json={"message": "events-one", "waitTimeoutMs": 1200, "idempotencyKey": f"events-1-{time.time_ns()}"},
            ).json()["data"]
            second = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/messages",
                json={
                    "message": "events-two",
                    "sessionId": first["sessionId"],
                    "waitTimeoutMs": 1200,
                    "idempotencyKey": f"events-2-{time.time_ns()}",
                },
            ).json()["data"]
            session_events_response = client.get(f"/api/v1/chatflows/{chatflow['id']}/sessions/{first['sessionId']}/events")
            run_events_response = client.get(f"/api/v1/chatflows/{chatflow['id']}/runs/{second['runId']}/events")

        self.assertEqual(session_events_response.status_code, 200, session_events_response.text)
        self.assertEqual(run_events_response.status_code, 200, run_events_response.text)
        session_events = session_events_response.json()["data"]["list"]
        run_events = run_events_response.json()["data"]["list"]
        self.assertIn(first["runId"], {event["runId"] for event in session_events})
        self.assertIn(second["runId"], {event["runId"] for event in session_events})
        self.assertEqual({event["runId"] for event in run_events}, {second["runId"]})
        self.assertIn("user_message", [event["type"] for event in run_events])
        self.assertIn("assistant_message", [event["type"] for event in run_events])

    def test_failed_turn_is_terminal_but_next_message_starts_an_isolated_turn(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_failure_then_success_chatflow(client)
            first = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/messages",
                json={
                    "message": "fail",
                    "waitTimeoutMs": 1200,
                    "idempotencyKey": f"failed-turn-{time.time_ns()}",
                },
            )
            self.assertEqual(first.status_code, 200, first.text)
            first_data = first.json()["data"]
            failed_session = client.get(
                f"/api/v1/chatflows/{chatflow['id']}/sessions/{first_data['sessionId']}"
            ).json()["data"]
            second = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/messages",
                json={
                    "message": "recover",
                    "sessionId": first_data["sessionId"],
                    "waitTimeoutMs": 1200,
                    "idempotencyKey": f"recovery-turn-{time.time_ns()}",
                },
            )
            self.assertEqual(second.status_code, 200, second.text)
            second_data = second.json()["data"]
            second_events = client.get(
                f"/api/v1/chatflows/{chatflow['id']}/runs/{second_data['runId']}/events"
            ).json()["data"]["list"]
            recovered_session = client.get(
                f"/api/v1/chatflows/{chatflow['id']}/sessions/{first_data['sessionId']}"
            ).json()["data"]

        self.assertEqual(first_data["status"], "FAILED")
        self.assertEqual(first_data["errorCode"], "WORKFLOW_NODE_FAILED")
        self.assertEqual(first_data["failure"]["nodeKey"], "code_1")
        self.assertEqual(failed_session["status"], "failed")
        self.assertEqual(second_data["status"], "SUCCEEDED")
        self.assertEqual(second_data["answer"], "reply:recover")
        self.assertNotEqual(second_data["runId"], first_data["runId"])
        self.assertFalse(second_data["idempotentReplay"])
        self.assertNotIn("failure", second_data)
        self.assertNotIn("workflow_run_failed", [event["type"] for event in second_events])
        self.assertEqual(recovered_session["status"], "completed")
        self.assertEqual(recovered_session["currentRunId"], second_data["runId"])


def _create_echo_chatflow(client: TestClient, label: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"196.1 Gateway {label} {time.time_ns()}",
            "description": "chatflow session gateway integration fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "answer", "output": "answer:{{start.sys.query}}"},
                },
            ],
            "edges": [{"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None}],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_failure_then_success_chatflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Runtime V2 Turn Isolation {time.time_ns()}",
            "description": "failed chatflow turn must not poison the next message",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "code_1",
                    "type": "CODE",
                    "name": "Failure switch",
                    "config": {
                        "language": "python",
                        "code": (
                            "result = {'content': 'reply:' + str(inputs.get('sys.query', ''))} "
                            "if inputs.get('sys.query') != 'fail' else 1 / 0"
                        ),
                        "outputParameters": [{"name": "content", "type": "string"}],
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "answer", "output": "{{code_1.content}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "code_1", "condition": None},
                {"sourceNodeKey": "code_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
