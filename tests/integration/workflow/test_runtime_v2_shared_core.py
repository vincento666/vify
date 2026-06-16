import time
import unittest
from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app


class RuntimeV2SharedCoreTest(unittest.TestCase):
    def test_runtime_events_are_schema_versioned_redacted_and_project_node_status(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_message_chatflow(client)
            started = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-v2",
                json={
                    "input": {
                        "sys.query": "Ada",
                        "api_key": "sk-secret",
                        "callerContext": {"sopKey": "refund_ticket", "routeTurnId": "turn-1"},
                    }
                },
            ).json()["data"]
            terminal = _wait_for_result(client, started["resultRef"])
            events = client.get(started["eventsRef"]).json()["data"]["list"]
            nodes = client.get(f"/api/v1/runtime-runs/{started['runId']}/nodes")

        self.assertEqual(terminal["status"], "SUCCEEDED")
        self.assertEqual(started["ownerType"], "CHATFLOW")
        self.assertEqual(started["ownerId"], chatflow["id"])
        first_payload = events[0]["payload"]
        self.assertEqual(first_payload["schemaVersion"], "runtime.v2.event/1")
        self.assertEqual(first_payload["input"]["api_key"], "[REDACTED]")
        self.assertEqual(first_payload["callerContext"]["sopKey"], "refund_ticket")
        self.assertIn("node_status_changed", [event["type"] for event in events])
        first_summary = events[0]["observability"]
        self.assertEqual(first_summary["sourceKind"], "chatflow")
        self.assertEqual(first_summary["eventMode"], "live")
        self.assertEqual(first_summary["correlationRefs"]["runtimeRunId"], started["runId"])
        self.assertEqual(first_summary["correlationRefs"]["sourceEventId"], events[0]["id"])
        self.assertEqual(first_summary["correlationRefs"]["sourceSequence"], events[0]["sequence"])

        self.assertEqual(nodes.status_code, 200)
        node_rows = nodes.json()["data"]["list"]
        self.assertEqual(nodes.json()["data"]["total"], len(node_rows))
        self.assertTrue(all(row["status"] == "COMPLETED" for row in node_rows))
        self.assertTrue(all(row["eventsRef"].endswith(f"/runtime-runs/{started['runId']}/events") for row in node_rows))
        self.assertTrue(all(row["observability"]["correlationRefs"]["runtimeRunId"] == started["runId"] for row in node_rows))

    def test_failed_node_marks_run_failed_and_stops_downstream_scheduling(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_failing_message_chatflow(client)
            started = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-v2",
                json={"input": {"sys.query": "Ada"}},
            ).json()["data"]
            failed = _wait_for_result(client, started["resultRef"], wanted_status="FAILED")
            nodes = client.get(started["nodesRef"]).json()["data"]["list"]
            events = client.get(started["eventsRef"]).json()["data"]["list"]

        self.assertEqual(failed["status"], "FAILED")
        self.assertEqual([node["nodeKey"] for node in nodes], ["llm_1"])
        self.assertEqual(nodes[0]["status"], "FAILED")
        self.assertEqual(nodes[0]["observability"]["nodeState"], "FAILED")
        self.assertIn("workflow_node_failed", [event["type"] for event in events])
        self.assertNotIn("end", [node["nodeKey"] for node in nodes])

    def test_cancel_endpoint_records_unsupported_event_without_terminal_rewrite(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_message_chatflow(client)
            started = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-v2",
                json={"input": {"sys.query": "Ada"}},
            ).json()["data"]
            cancelled = client.post(f"/api/v1/runtime-runs/{started['runId']}/cancel")
            events = client.get(started["eventsRef"]).json()["data"]["list"]

        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(cancelled.json()["data"]["status"], "cancel_unsupported")
        self.assertIn("runtime_cancel_unsupported", [event["type"] for event in events])


def _wait_for_result(
    client: TestClient,
    result_ref: str,
    wanted_status: str = "SUCCEEDED",
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


def _create_message_chatflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Runtime V2 Shared Core {datetime.now().timestamp()}",
            "description": "",
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


def _create_failing_message_chatflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Runtime V2 Failed Node {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {"nodeKey": "llm_1", "type": "MESSAGE", "name": "Message", "config": {"raiseError": "node failed"}},
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final", "output": "done"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "llm_1", "condition": None},
                {"sourceNodeKey": "llm_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
