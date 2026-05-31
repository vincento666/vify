import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class ChatflowResourceSeparationTest(unittest.TestCase):
    def test_chatflow_and_workflow_share_graph_tables_but_are_listed_separately(self) -> None:
        suffix = time.time_ns()

        with TestClient(app) as client:
            workflow = _create_flow(client, "/api/v1/workflows", f"Workflow {suffix}")
            chatflow = _create_flow(client, "/api/v1/chatflows", f"Chatflow {suffix}")

            workflow_list = client.get("/api/v1/workflows", params={"page": 1, "pageSize": 50})
            chatflow_list = client.get("/api/v1/chatflows", params={"page": 1, "pageSize": 50})
            workflow_detail_for_chatflow = client.get(f"/api/v1/workflows/{chatflow['id']}")
            chatflow_detail = client.get(f"/api/v1/chatflows/{chatflow['id']}")

        self.assertEqual(workflow["flowType"], "WORKFLOW")
        self.assertEqual(chatflow["flowType"], "CHATFLOW")
        self.assertTrue(any(item["id"] == workflow["id"] for item in workflow_list.json()["data"]["list"]))
        self.assertFalse(any(item["id"] == chatflow["id"] for item in workflow_list.json()["data"]["list"]))
        self.assertTrue(any(item["id"] == chatflow["id"] for item in chatflow_list.json()["data"]["list"]))
        self.assertFalse(any(item["id"] == workflow["id"] for item in chatflow_list.json()["data"]["list"]))
        self.assertEqual(workflow_detail_for_chatflow.status_code, 404)
        self.assertEqual(chatflow_detail.status_code, 200)
        self.assertEqual(chatflow_detail.json()["data"]["nodes"][0]["config"]["outputVariables"][0], "sys.query")


def _create_flow(client: TestClient, url: str, name: str) -> dict[str, object]:
    response = client.post(
        url,
        json={
            "name": name,
            "description": "",
            "nodes": [
                {
                    "nodeKey": "start",
                    "type": "START",
                    "name": "Start",
                    "config": {"outputVariables": ["sys.query"]},
                },
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "output"}},
            ],
            "edges": [{"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None}],
        },
    )
    self_message = response.text
    assert response.status_code == 200, self_message
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
