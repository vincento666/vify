import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class RuntimeV2PublishedVersionTargetingTest(unittest.TestCase):
    def test_workflow_v2_can_run_active_or_targeted_published_version(self) -> None:
        with TestClient(app) as client:
            workflow = _create_linear_flow(client, "/api/v1/workflows", "workflow-v1")
            publish_v1 = client.post(f"/api/v1/workflows/{workflow['id']}/publish").json()["data"]
            _update_linear_flow(client, "/api/v1/workflows", workflow["id"], "workflow-v2")
            publish_v2 = client.post(f"/api/v1/workflows/{workflow['id']}/publish").json()["data"]

            active_started = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-v2",
                json={"input": {"sys.query": "active"}},
            ).json()["data"]
            targeted_started = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-v2",
                json={"input": {"sys.query": "targeted"}, "versionId": publish_v1["id"]},
            ).json()["data"]
            active_result = _wait_for_result(client, active_started["resultRef"])
            targeted_result = _wait_for_result(client, targeted_started["resultRef"])
            targeted_debug = client.get(
                f"/api/v1/workflows/{workflow['id']}/runs/{targeted_started['runId']}/debug"
            ).json()["data"]

        self.assertEqual(active_started["versionId"], publish_v2["id"])
        self.assertEqual(active_started["version"], 2)
        self.assertEqual(active_result["output"], {"final": "workflow-v2"})
        self.assertEqual(active_result["versionId"], publish_v2["id"])
        self.assertEqual(targeted_started["versionId"], publish_v1["id"])
        self.assertEqual(targeted_started["version"], 1)
        self.assertEqual(targeted_result["output"], {"final": "workflow-v1"})
        self.assertEqual(targeted_result["versionId"], publish_v1["id"])
        self.assertEqual(targeted_debug["versionId"], publish_v1["id"])
        self.assertEqual(targeted_debug["version"], 1)

    def test_chatflow_v2_can_run_active_or_targeted_published_version(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_linear_flow(client, "/api/v1/chatflows", "chatflow-v1")
            publish_v1 = client.post(f"/api/v1/chatflows/{chatflow['id']}/publish").json()["data"]
            _update_linear_flow(client, "/api/v1/chatflows", chatflow["id"], "chatflow-v2")
            publish_v2 = client.post(f"/api/v1/chatflows/{chatflow['id']}/publish").json()["data"]

            active_started = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-v2",
                json={"input": {"sys.query": "active", "sys.conversation_id": f"active-{time.time_ns()}"}},
            ).json()["data"]
            targeted_started = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-v2",
                json={
                    "input": {"sys.query": "targeted", "sys.conversation_id": f"targeted-{time.time_ns()}"},
                    "versionId": publish_v1["id"],
                },
            ).json()["data"]
            active_result = _wait_for_result(client, active_started["resultRef"])
            targeted_result = _wait_for_result(client, targeted_started["resultRef"])
            targeted_debug = client.get(
                f"/api/v1/chatflows/{chatflow['id']}/runs/{targeted_started['runId']}/debug"
            ).json()["data"]

        self.assertEqual(active_started["versionId"], publish_v2["id"])
        self.assertEqual(active_started["version"], 2)
        self.assertEqual(active_result["output"], {"final": "chatflow-v2"})
        self.assertEqual(active_result["versionId"], publish_v2["id"])
        self.assertEqual(targeted_started["versionId"], publish_v1["id"])
        self.assertEqual(targeted_started["version"], 1)
        self.assertEqual(targeted_result["output"], {"final": "chatflow-v1"})
        self.assertEqual(targeted_result["versionId"], publish_v1["id"])
        self.assertEqual(targeted_debug["versionId"], publish_v1["id"])
        self.assertEqual(targeted_debug["version"], 1)

    def test_runtime_v2_rejects_unknown_or_cross_flow_version_id(self) -> None:
        with TestClient(app) as client:
            workflow = _create_linear_flow(client, "/api/v1/workflows", "workflow-active")
            client.post(f"/api/v1/workflows/{workflow['id']}/publish")
            chatflow = _create_linear_flow(client, "/api/v1/chatflows", "chatflow-active")
            chatflow_version = client.post(f"/api/v1/chatflows/{chatflow['id']}/publish").json()["data"]

            unknown = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-v2",
                json={"input": {}, "versionId": 999999999},
            )
            cross_flow = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-v2",
                json={"input": {}, "versionId": chatflow_version["id"]},
            )

        self.assertEqual(unknown.status_code, 404, unknown.text)
        self.assertIn("Published version not found", unknown.json()["message"])
        self.assertNotIn("eventStreamRef", unknown.json())
        self.assertEqual(cross_flow.status_code, 404, cross_flow.text)
        self.assertIn("Published version not found", cross_flow.json()["message"])
        self.assertNotIn("eventStreamRef", cross_flow.json())

    def test_runtime_v2_resume_after_draft_edit_uses_targeted_version(self) -> None:
        with TestClient(app) as client:
            workflow = _create_question_flow(client, "target-v1")
            publish_v1 = client.post(f"/api/v1/workflows/{workflow['id']}/publish").json()["data"]
            _update_question_flow(client, workflow["id"], "active-v2")
            client.post(f"/api/v1/workflows/{workflow['id']}/publish")

            started = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-v2",
                json={"input": {"sys.query": "start"}, "versionId": publish_v1["id"]},
            ).json()["data"]
            interrupted = _wait_for_result(client, started["resultRef"], wanted_status="INTERRUPTED")
            _update_question_flow(client, workflow["id"], "draft-after-start")
            resumed = client.post(
                f"/api/v1/runtime-runs/{started['runId']}/resume",
                json={"resumeData": {"answer": "yes"}, "idempotencyKey": f"target-resume-{time.time_ns()}"},
            ).json()["data"]
            debug = client.get(f"/api/v1/workflows/{workflow['id']}/runs/{started['runId']}/debug").json()["data"]

        self.assertEqual(started["versionId"], publish_v1["id"])
        self.assertEqual(started["version"], 1)
        self.assertEqual(interrupted["versionId"], publish_v1["id"])
        self.assertEqual(resumed["status"], "SUCCEEDED")
        self.assertEqual(resumed["output"], {"final": "target-v1 answer=yes"})
        self.assertEqual(resumed["versionId"], publish_v1["id"])
        self.assertEqual(debug["versionId"], publish_v1["id"])


def _wait_for_result(
    client: TestClient,
    result_ref: str,
    wanted_status: str = "SUCCEEDED",
    timeout: float = 5.0,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(result_ref)
        latest = response.json()["data"]
        if latest["status"] == wanted_status:
            return latest
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for {wanted_status}; latest={latest}")


def _create_linear_flow(client: TestClient, base_url: str, output: str) -> dict[str, object]:
    response = client.post(
        base_url,
        json={
            "name": f"Runtime V2 Version Target {time.time_ns()}",
            "description": "",
            "nodes": _linear_nodes(output),
            "edges": _linear_edges(),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _update_linear_flow(client: TestClient, base_url: str, flow_id: int, output: str) -> None:
    response = client.put(
        f"{base_url}/{flow_id}",
        json={"nodes": _linear_nodes(output), "edges": _linear_edges()},
    )
    assert response.status_code == 200, response.text


def _linear_nodes(output: str) -> list[dict[str, object]]:
    return [
        {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
        {
            "nodeKey": "message_1",
            "type": "MESSAGE",
            "name": "Message",
            "config": {"content": output, "outputVariable": "content"},
        },
        {
            "nodeKey": "end",
            "type": "END",
            "name": "End",
            "config": {"outputVariable": "final", "output": "{{message_1.content}}"},
        },
    ]


def _linear_edges() -> list[dict[str, object]]:
    return [
        {"sourceNodeKey": "start", "targetNodeKey": "message_1", "condition": None},
        {"sourceNodeKey": "message_1", "targetNodeKey": "end", "condition": None},
    ]


def _create_question_flow(client: TestClient, output: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Runtime V2 Resume Version Target {time.time_ns()}",
            "description": "",
            "nodes": _question_nodes(output),
            "edges": _question_edges(),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _update_question_flow(client: TestClient, workflow_id: int, output: str) -> None:
    response = client.put(
        f"/api/v1/workflows/{workflow_id}",
        json={"nodes": _question_nodes(output), "edges": _question_edges()},
    )
    assert response.status_code == 200, response.text


def _question_nodes(output: str) -> list[dict[str, object]]:
    return [
        {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
        {
            "nodeKey": "question_1",
            "type": "QUESTION",
            "name": "Question",
            "config": {"question": "Continue?", "outputVariable": "answer", "answerType": "text"},
        },
        {
            "nodeKey": "message_1",
            "type": "MESSAGE",
            "name": "Message",
            "config": {"content": f"{output} answer={{{{question_1.answer}}}}", "outputVariable": "content"},
        },
        {
            "nodeKey": "end",
            "type": "END",
            "name": "End",
            "config": {"outputVariable": "final", "output": "{{message_1.content}}"},
        },
    ]


def _question_edges() -> list[dict[str, object]]:
    return [
        {"sourceNodeKey": "start", "targetNodeKey": "question_1", "condition": None},
        {"sourceNodeKey": "question_1", "targetNodeKey": "message_1", "condition": None},
        {"sourceNodeKey": "message_1", "targetNodeKey": "end", "condition": None},
    ]


if __name__ == "__main__":
    unittest.main()
