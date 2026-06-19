import unittest

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from app.modules.customer_assistant.infra.schema import (
    customer_assistant_tables,
    register_customer_assistant_tables,
)
from tests.support.mysql import mysql8_unittest_database


class CustomerAssistantMessageGatewayContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self._database = mysql8_unittest_database(
            self,
            "customer_assistant_message_gateway",
            tables=customer_assistant_tables(),
            register=register_customer_assistant_tables,
        )
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(runtime_lab_sop_chatflow_ids=None)

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_message_gateway_auto_creates_session_and_projects_chat_events(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/customer-assistant/messages",
                json={"message": "我要退票", "idempotencyKey": "gateway-auto-1"},
            )

            self.assertEqual(response.status_code, 200, response.text)
            data = response.json()["data"]
            session_id = data["sessionId"]
            events = client.get(data["eventsRef"]).json()["data"]["list"]

            delta = next(event for event in events if event["type"] == "message.delta")
            completed = next(event for event in events if event["type"] == "message.completed")
            requires_input = next(event for event in events if event["type"] == "requires_input")
            run_completed = next(event for event in events if event["type"] == "run.completed")
            with client.stream(
                "GET",
                f"/api/v1/customer-assistant/sessions/{session_id}/events/stream"
                f"?afterSequence={delta['sequence']}&_testLimit=1",
            ) as stream:
                recovered = _read_sse_event(stream)

        self.assertEqual(data["sessionId"], session_id)
        self.assertEqual(data["conversationId"], f"customer-assistant:{session_id}")
        self.assertEqual(data["status"], "WAITING")
        self.assertEqual(data["requiresInput"], True)
        self.assertTrue(data["answer"])
        self.assertIsInstance(data["latencyMs"], int)
        self.assertGreaterEqual(data["latencyMs"], 0)
        self.assertEqual(
            data["usage"],
            {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0, "estimated": False},
        )
        self.assertFalse(data["retryable"])
        self.assertEqual(data["runSummary"]["status"], "WAITING")
        self.assertEqual(data["runSummary"]["eventCount"], len(data["eventSummary"]))
        self.assertTrue(any(event["type"] == "message.completed" for event in data["eventSummary"]))
        self.assertTrue(all("payload" not in event for event in data["eventSummary"]))
        self.assertEqual(data["eventsRef"], f"/api/v1/customer-assistant/sessions/{session_id}/events")
        self.assertEqual(
            data["eventStreamRef"],
            f"/api/v1/customer-assistant/sessions/{session_id}/events/stream?afterSequence=0",
        )
        self.assertEqual(completed["payload"]["answer"], data["answer"])
        self.assertEqual(requires_input["runId"], data["runId"])
        self.assertEqual(run_completed["payload"]["status"], "WAITING")
        self.assertEqual(recovered["type"], "message.completed")

    def test_session_message_gateway_reuses_session_and_replays_idempotency(self) -> None:
        with TestClient(app) as client:
            first = client.post(
                "/api/v1/customer-assistant/messages",
                json={"message": "我要退票", "idempotencyKey": "gateway-reuse-1"},
            ).json()["data"]
            second_response = client.post(
                f"/api/v1/customer-assistant/sessions/{first['sessionId']}/messages",
                json={"message": "订单号 TK-100", "idempotencyKey": "gateway-reuse-2"},
            )
            replay_response = client.post(
                f"/api/v1/customer-assistant/sessions/{first['sessionId']}/messages",
                json={"message": "订单号 TK-100", "idempotencyKey": "gateway-reuse-2"},
            )
            events = client.get(second_response.json()["data"]["eventsRef"]).json()["data"]["list"]

        self.assertEqual(second_response.status_code, 200, second_response.text)
        self.assertEqual(replay_response.status_code, 200, replay_response.text)
        second = second_response.json()["data"]
        replay = replay_response.json()["data"]
        self.assertEqual(second["sessionId"], first["sessionId"])
        self.assertEqual(second["conversationId"], first["conversationId"])
        self.assertNotEqual(second["runId"], first["runId"])
        self.assertEqual(replay["runId"], second["runId"])
        self.assertEqual(replay["replayed"], True)
        completed_events = [
            event
            for event in events
            if event["type"] == "message.completed" and event["runId"] == second["runId"]
        ]
        self.assertEqual(len(completed_events), 1)

    def _session_override(self):
        with self._factory() as session:
            yield session


def _read_sse_event(stream) -> dict:
    for line in stream.iter_lines():
        if not line.startswith("data:"):
            continue
        import json

        return json.loads(line[len("data:") :].strip())
    raise AssertionError("No SSE data frame returned")
