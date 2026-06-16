import time
import unittest
from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app


class WorkflowRuntimeV2FacadeTest(unittest.TestCase):
    def test_workflow_v2_run_uses_published_snapshot_and_preserves_caller_context(self) -> None:
        with TestClient(app) as client:
            workflow = _create_workflow(client, message="published")
            version = client.post(f"/api/v1/workflows/{workflow['id']}/publish").json()["data"]
            first = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-v2",
                json={
                    "input": {
                        "sys.query": "pricing",
                        "callerContext": {"router": "sop", "traceId": "wf-v2-ctx"},
                    },
                    "idempotencyKey": "workflow-v2-idempotent-1",
                },
            )
            duplicate = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-v2",
                json={
                    "input": {
                        "sys.query": "pricing",
                        "callerContext": {"router": "sop", "traceId": "wf-v2-ctx"},
                    },
                    "idempotencyKey": "workflow-v2-idempotent-1",
                },
            )
            _replace_workflow_message(client, workflow["id"], message="draft-edited")
            started = first.json()["data"]
            terminal = _wait_for_result(client, started["resultRef"])
            events = client.get(started["eventsRef"]).json()["data"]["list"]
            observe_detail = client.get(f"/api/v1/observe/runs/{started['runId']}").json()["data"]
            debug = client.get(f"/api/v1/workflows/{workflow['id']}/runs/{started['runId']}/debug").json()["data"]

        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(duplicate.status_code, 200, duplicate.text)
        self.assertFalse(started["idempotentReplay"])
        self.assertTrue(duplicate.json()["data"]["idempotentReplay"])
        self.assertEqual(started["runId"], duplicate.json()["data"]["runId"])
        self.assertEqual(started["ownerType"], "WORKFLOW")
        self.assertEqual(started["ownerId"], workflow["id"])
        self.assertEqual(started["workflowId"], workflow["id"])
        self.assertEqual(started["versionId"], version["id"])
        self.assertEqual(started["version"], version["version"])
        self.assertEqual(terminal["status"], "SUCCEEDED")
        self.assertEqual(terminal["output"], {"final": "published"})
        self.assertTrue(any(event["payload"]["callerContext"]["traceId"] == "wf-v2-ctx" for event in events))
        self.assertEqual(observe_detail["sessionId"], "")
        self.assertEqual(debug["ownerType"], "WORKFLOW")
        self.assertEqual([node["status"] for node in debug["nodeDetails"]], ["SUCCEEDED", "SUCCEEDED"])
        self.assertTrue(any(event["type"] == "workflow_node_completed" for event in debug["events"]))

    def test_workflow_v2_rejects_unsupported_graph_without_partial_execution(self) -> None:
        with TestClient(app) as client:
            workflow = _create_workflow(client, message="unsupported", node_type="LLM")
            client.post(f"/api/v1/workflows/{workflow['id']}/publish")
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-v2",
                json={"input": {"sys.query": "hello"}},
            )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertIn("unsupportedNodes", payload["message"])
        self.assertNotIn("eventStreamRef", payload)

    def test_legacy_workflow_run_response_stays_compatible(self) -> None:
        with TestClient(app) as client:
            workflow = _create_workflow(client, message="legacy")
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"sys.query": "hello"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"], {"final": "legacy"})
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


def _create_workflow(client: TestClient, *, message: str, node_type: str = "MESSAGE") -> dict[str, object]:
    middle_config = {"content": message, "outputVariable": "content"}
    if node_type == "LLM":
        middle_config = {"prompt": message, "outputVariable": "content"}
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Workflow V2 Facade {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {"nodeKey": "middle_1", "type": node_type, "name": "Middle", "config": middle_config},
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{middle_1.content}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "middle_1", "condition": None},
                {"sourceNodeKey": "middle_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _replace_workflow_message(client: TestClient, workflow_id: int, *, message: str) -> None:
    response = client.put(
        f"/api/v1/workflows/{workflow_id}",
        json={
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "middle_1",
                    "type": "MESSAGE",
                    "name": "Middle",
                    "config": {"content": message, "outputVariable": "content"},
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{middle_1.content}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "middle_1", "condition": None},
                {"sourceNodeKey": "middle_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text


if __name__ == "__main__":
    unittest.main()
