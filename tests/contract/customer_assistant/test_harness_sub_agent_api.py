import json
import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from tests.support.mysql import mysql8_unittest_database
from app.modules.customer_assistant.harness_adapter import summarize_sub_agent_result
from app.modules.customer_assistant.infra.schema import (
    customer_assistant_tables,
    register_customer_assistant_tables,
)


class CustomerAssistantHarnessSubAgentApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self._database = mysql8_unittest_database(self, "customer_assistant_harness", tables=customer_assistant_tables(), register=register_customer_assistant_tables)
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(runtime_lab_sop_chatflow_ids=None)

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_spawn_sub_agent_returns_run_refs_events_and_fetchable_result(self) -> None:
        with TestClient(app) as client:
            spawned = client.post(
                "/api/v1/customer-assistant/harness/spawn-sub-agent",
                json={
                    "tool": "spawn_sub_agent",
                    "arguments": {
                        "agentType": "customer_assistant",
                        "input": {"message": "我要退票", "actor": "customer"},
                        "eventLevel": "L1",
                    },
                },
            )
            data = spawned.json()["data"]
            result = client.get(data["resultRef"])
            events = client.get(f"/api/v1/customer-assistant/sessions/{data['sessionId']}/events")
            with client.stream("GET", f"{data['eventStreamRef']}&_testLimit=1") as stream:
                first_sse_event = _read_first_sse_event(stream)

        self.assertEqual(spawned.status_code, 200)
        self.assertEqual(data["subAgentRunId"], f"customer-assistant-run-{data['runId']}")
        self.assertEqual(data["status"], "running")
        self.assertEqual(data["agentType"], "customer_assistant")
        self.assertIn("/events/stream?afterSequence=0", data["eventStreamRef"])
        self.assertIn(f"/api/v1/customer-assistant/runs/{data['runId']}", data["resultRef"])
        self.assertFalse(data["cancellation"]["supported"])
        self.assertFalse(data["workerAsyncRefs"]["supported"])
        self.assertIsNone(data["workerAsyncRefs"]["workerRunId"])
        self.assertIsNone(data["workerAsyncRefs"]["workerStatusRef"])
        self.assertIn("No durable async worker run", data["workerAsyncRefs"]["reason"])

        result_data = result.json()["data"]
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result_data["status"], "completed")
        self.assertEqual(result_data["result"]["runId"], data["runId"])
        self.assertIn("operatorRecommendation", summarize_sub_agent_result(result_data))

        event_types = [event["type"] for event in events.json()["data"]["list"]]
        self.assertEqual(first_sse_event["type"], "sub_agent_spawned")
        self.assertIn("sub_agent_started", event_types)
        self.assertIn("sub_agent_progress", event_types)
        self.assertIn("sub_agent_completed", event_types)

    def test_spawn_sub_agent_does_not_expose_payload_only_worker_run_refs(self) -> None:
        with TestClient(app) as client:
            spawned = client.post(
                "/api/v1/customer-assistant/harness/spawn-sub-agent",
                json={
                    "tool": "spawn_sub_agent",
                    "arguments": {
                        "agentType": "customer_assistant",
                        "input": {"message": "我要退票", "actor": "customer"},
                    },
                },
            ).json()["data"]
        self.assertFalse(spawned["workerAsyncRefs"]["supported"])
        self.assertIsNone(spawned["workerAsyncRefs"]["workerRunId"])
        self.assertIn("No durable async worker run", spawned["workerAsyncRefs"]["reason"])

    def test_spawned_baggage_sub_agent_result_exposes_real_worker_refs(self) -> None:
        with TestClient(app) as client:
            spawned = client.post(
                "/api/v1/customer-assistant/harness/spawn-sub-agent",
                json={
                    "tool": "spawn_sub_agent",
                    "arguments": {
                        "agentType": "customer_assistant",
                        "input": {"message": "行李额度是多少", "actor": "customer"},
                    },
                },
            ).json()["data"]
            result = client.get(spawned["resultRef"]).json()["data"]["result"]
            refs = result["taskSummaries"][0]["workerAsyncRefs"]
            worker_status = client.get(refs["workerStatusRef"])

        self.assertTrue(refs["supported"])
        self.assertEqual(worker_status.status_code, 200)
        self.assertEqual(worker_status.json()["data"]["status"], "COMPLETED")

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session


def _read_first_sse_event(response) -> dict[str, object]:
    for line in response.iter_lines():
        if line.startswith("data: "):
            return json.loads(line.removeprefix("data: "))
    raise AssertionError("No SSE data event emitted")


if __name__ == "__main__":
    unittest.main()
