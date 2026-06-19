import json
import time
import unittest
from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app


class WorkflowRunGatewayApiTest(unittest.TestCase):
    def test_workflow_runs_endpoint_is_async_runtime_gateway(self) -> None:
        with TestClient(app) as client:
            workflow = _create_workflow(client, message="published gateway")
            version = client.post(f"/api/v1/workflows/{workflow['id']}/publish").json()["data"]
            started = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"sys.query": "gateway"}, "versionId": version["id"], "idempotencyKey": "199-runs"},
            )
            replay = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"sys.query": "gateway"}, "versionId": version["id"], "idempotencyKey": "199-runs"},
            )
            data = started.json()["data"]
            terminal = _wait_for_result(client, data["resultRef"])
            events = client.get(data["eventsRef"]).json()["data"]["list"]
            nodes = client.get(data["nodesRef"]).json()["data"]["list"]

        self.assertEqual(started.status_code, 200, started.text)
        self.assertEqual(data["ownerType"], "WORKFLOW")
        self.assertEqual(data["ownerId"], workflow["id"])
        self.assertEqual(data["workflowId"], workflow["id"])
        self.assertEqual(data["versionId"], version["id"])
        self.assertNotIn("output", data)
        self.assertEqual(replay.json()["data"]["runId"], data["runId"])
        self.assertTrue(replay.json()["data"]["idempotentReplay"])
        self.assertEqual(data["statusRef"], f"/api/v1/runtime-runs/{data['runId']}")
        self.assertEqual(data["eventsRef"], f"/api/v1/runtime-runs/{data['runId']}/events")
        self.assertEqual(data["nodesRef"], f"/api/v1/runtime-runs/{data['runId']}/nodes")
        self.assertEqual(data["resultRef"], f"/api/v1/runtime-runs/{data['runId']}/result")
        self.assertEqual(terminal["status"], "SUCCEEDED")
        self.assertEqual(terminal["output"], {"final": "published gateway"})
        self.assertTrue(any(event["type"] == "workflow_run_started" for event in events))
        self.assertEqual([node["status"] for node in nodes], ["COMPLETED", "COMPLETED"])

    def test_workflow_runs_stream_starts_run_and_streams_events(self) -> None:
        with TestClient(app) as client:
            workflow = _create_workflow(client, message="stream gateway")
            client.post(f"/api/v1/workflows/{workflow['id']}/publish")
            with client.stream(
                "POST",
                f"/api/v1/workflows/{workflow['id']}/runs:stream?_testLimit=1",
                json={"input": {"sys.query": "stream gateway"}, "idempotencyKey": "199-stream"},
            ) as stream:
                event = _read_sse_event(stream)

        self.assertEqual(event["type"], "workflow_run_started")
        self.assertEqual(event["payload"]["ownerType"], "WORKFLOW")
        self.assertEqual(event["payload"]["ownerId"], workflow["id"])
        self.assertIn("/api/v1/runtime-runs/", event["payload"]["resultRef"])

    def test_workflow_runs_legacy_keeps_sync_compatibility(self) -> None:
        with TestClient(app) as client:
            workflow = _create_workflow(client, message="legacy gateway")
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-legacy",
                json={"input": {"sys.query": "legacy"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"], {"final": "legacy gateway"})
        self.assertIn("debugUrl", data)


def _wait_for_result(client: TestClient, result_ref: str, timeout: float = 5.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        latest = client.get(result_ref).json()["data"]
        if latest["status"] in {"SUCCEEDED", "FAILED", "INTERRUPTED"}:
            return latest
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for terminal result; latest={latest}")


def _read_sse_event(stream) -> dict[str, object]:
    data = []
    for line in stream.iter_lines():
        if line.startswith("data:"):
            data.append(line[len("data:") :].strip())
        if data and not line:
            return json.loads("\n".join(data))
    if data:
        return json.loads("\n".join(data))
    raise AssertionError("No SSE data frame returned")


def _create_workflow(client: TestClient, *, message: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Workflow Run Gateway {datetime.now().timestamp()}",
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
