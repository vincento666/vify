import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class ComposerDebugUrlContractTest(unittest.TestCase):
    def test_workflow_run_returns_canvas_debug_url_without_payload_leakage(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            workflow = _create_workflow(client, stamp)
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-legacy",
                json={"input": {"USER_INPUT": "secret debug payload"}},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        expected = f"/workflows/{workflow['id']}/canvas?runId={data['runId']}&debug=1"
        self.assertEqual(data["debugUrl"], expected)
        self.assertEqual(data["debug_url"], expected)
        self.assertNotIn("secret", data["debugUrl"])
        self.assertNotIn(str(data["output"]), data["debugUrl"])

    def test_published_chatflow_run_returns_canvas_debug_url_without_payload_leakage(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_chatflow(client, stamp)
            publish_response = client.post(f"/api/v1/chatflows/{chatflow['id']}/publish")
            self.assertEqual(publish_response.status_code, 200, publish_response.text)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/published-runs",
                json={
                    "input": {
                        "sys.query": "secret chatflow payload",
                        "sys.conversation_id": f"conv-0215-{stamp}",
                        "sys.user_id": "user-0215",
                        "sys.channel": "api",
                    }
                },
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        expected = f"/chatflows/{chatflow['id']}/canvas?runId={data['runId']}&debug=1"
        self.assertEqual(data["debugUrl"], expected)
        self.assertEqual(data["debug_url"], expected)
        self.assertNotIn("secret", data["debugUrl"])
        self.assertNotIn(str(data["output"]), data["debugUrl"])


def _create_workflow(client: TestClient, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"021.5 Workflow Debug URL {stamp}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "answer", "output": "echo {{start.USER_INPUT}}"}},
            ],
            "edges": [{"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None}],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_chatflow(client: TestClient, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"021.5 Chatflow Debug URL {stamp}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {"nodeKey": "message_1", "type": "MESSAGE", "name": "Message", "config": {"content": "hello {{start.sys.query}}", "outputVariable": "content"}},
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final", "output": "{{message_1.content}}"}},
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
