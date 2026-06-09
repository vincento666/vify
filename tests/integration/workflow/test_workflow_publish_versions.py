import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class WorkflowPublishVersionsTest(unittest.TestCase):
    def test_workflow_publish_creates_immutable_versions_and_rollback_changes_active_run(self) -> None:
        with TestClient(app) as client:
            workflow = self._create_workflow(client, "v1")
            publish_v1 = client.post(f"/api/v1/workflows/{workflow['id']}/publish")

            self._update_workflow_output(client, workflow["id"], "v2")
            publish_v2 = client.post(f"/api/v1/workflows/{workflow['id']}/publish")
            active_v2_run = client.post(f"/api/v1/workflows/{workflow['id']}/published-runs", json={"input": {}})

            versions_response = client.get(f"/api/v1/workflows/{workflow['id']}/versions")
            rollback_response = client.post(
                f"/api/v1/workflows/{workflow['id']}/versions/{publish_v1.json()['data']['id']}/rollback"
            )
            active_v1_run = client.post(f"/api/v1/workflows/{workflow['id']}/published-runs", json={"input": {}})

        self.assertEqual(publish_v1.status_code, 200)
        self.assertEqual(publish_v1.json()["data"]["version"], 1)
        self.assertEqual(publish_v2.status_code, 200)
        self.assertEqual(publish_v2.json()["data"]["version"], 2)
        self.assertEqual(active_v2_run.json()["data"]["output"]["final"], "v2")
        versions = versions_response.json()["data"]["list"]
        self.assertEqual([item["version"] for item in versions], [2, 1])
        self.assertTrue(next(item for item in versions if item["version"] == 2)["active"])
        self.assertEqual(rollback_response.status_code, 200)
        self.assertEqual(rollback_response.json()["data"]["version"], 1)
        self.assertTrue(rollback_response.json()["data"]["active"])
        self.assertEqual(active_v1_run.json()["data"]["output"]["final"], "v1")

    def test_chatflow_publish_requires_channel_config_and_valid_graph(self) -> None:
        with TestClient(app) as client:
            chatflow = self._create_chatflow(client)
            publish_response = client.post(f"/api/v1/chatflows/{chatflow['id']}/publish")
            versions_response = client.get(f"/api/v1/chatflows/{chatflow['id']}/versions")

        self.assertEqual(publish_response.status_code, 200)
        self.assertEqual(publish_response.json()["data"]["flowType"], "CHATFLOW")
        self.assertEqual(publish_response.json()["data"]["version"], 1)
        self.assertEqual(versions_response.json()["data"]["total"], 1)

    def test_chatflow_publish_rejects_transfer_to_human_without_queue(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/chatflows",
                json={
                    "name": f"Invalid Handoff Publish {time.time_ns()}",
                    "description": "",
                    "nodes": [
                        {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                        {
                            "nodeKey": "handoff_1",
                            "type": "TRANSFER_TO_HUMAN",
                            "name": "Handoff",
                            "config": {"queue": "", "message": "转人工"},
                        },
                        {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final"}},
                    ],
                    "edges": [
                        {"sourceNodeKey": "start", "targetNodeKey": "handoff_1", "condition": None},
                        {"sourceNodeKey": "handoff_1", "targetNodeKey": "end", "condition": None},
                    ],
                },
            )
            chatflow = response.json()["data"]
            publish_response = client.post(f"/api/v1/chatflows/{chatflow['id']}/publish")

        self.assertEqual(publish_response.status_code, 400)
        self.assertIn("handoff queue", publish_response.json()["message"])

    def _create_workflow(self, client: TestClient, output: str) -> dict:
        response = client.post(
            "/api/v1/workflows",
            json={
                "name": f"Publish Workflow {time.time_ns()}",
                "description": "",
                "nodes": [
                    {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                    {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final", "output": output}},
                ],
                "edges": [{"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None}],
            },
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["data"]

    def _update_workflow_output(self, client: TestClient, workflow_id: int, output: str) -> None:
        response = client.put(
            f"/api/v1/workflows/{workflow_id}",
            json={
                "nodes": [
                    {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                    {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final", "output": output}},
                ],
                "edges": [{"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None}],
            },
        )
        self.assertEqual(response.status_code, 200)

    def _create_chatflow(self, client: TestClient) -> dict:
        response = client.post(
            "/api/v1/chatflows",
            json={
                "name": f"Publish Chatflow {time.time_ns()}",
                "description": "",
                "nodes": [
                    {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                    {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final", "output": "ok"}},
                ],
                "edges": [{"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None}],
            },
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
