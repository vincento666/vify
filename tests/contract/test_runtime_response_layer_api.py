import time
import unittest
from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app


class RuntimeResponseLayerApiTest(unittest.TestCase):
    def test_runtime_result_returns_summary_events_without_hiding_debug_events(self) -> None:
        with TestClient(app) as client:
            workflow = _create_workflow(client, message="response layer")
            version = client.post(f"/api/v1/workflows/{workflow['id']}/publish").json()["data"]
            started = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={
                    "input": {"sys.query": "response layer"},
                    "versionId": version["id"],
                    "idempotencyKey": f"response-layer-{time.time_ns()}",
                },
            )
            self.assertEqual(started.status_code, 200, started.text)
            refs = started.json()["data"]
            result = _wait_for_result(client, refs["resultRef"])
            debug_events = client.get(refs["eventsRef"]).json()["data"]["list"]

        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(result["statusRef"], f"/api/v1/runtime-runs/{refs['runId']}")
        self.assertEqual(result["result"], {"final": "response layer"})
        self.assertIsInstance(result["latencyMs"], int)
        self.assertGreaterEqual(result["latencyMs"], 0)
        self.assertEqual(
            result["usage"],
            {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0, "estimated": False},
        )
        self.assertFalse(result["retryable"])
        self.assertTrue(result["events"])
        self.assertTrue(all("payload" not in event for event in result["events"]))
        self.assertTrue(all("output" not in str(event) for event in result["events"]))
        self.assertTrue(any(event["type"] == "workflow_node_completed" for event in result["events"]))

        completed = next(event for event in debug_events if event["type"] == "workflow_node_completed")
        self.assertIn("payload", completed)
        self.assertIn("output", completed["payload"])


def _wait_for_result(client: TestClient, result_ref: str, timeout: float = 5.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        latest = client.get(result_ref).json()["data"]
        if latest["status"] in {"SUCCEEDED", "FAILED", "INTERRUPTED", "CANCELLED"}:
            return latest
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for terminal result; latest={latest}")


def _create_workflow(client: TestClient, *, message: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Runtime Response Layer {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "message_1",
                    "type": "MESSAGE",
                    "name": "Message",
                    "config": {"content": message, "outputVariable": "content"},
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{message_1.content}}"},
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
