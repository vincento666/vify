import unittest

from fastapi.testclient import TestClient

from app.main import app


class WorkflowPublishStatusTest(unittest.TestCase):
    def test_update_status_to_published_preserves_graph(self) -> None:
        with TestClient(app) as client:
            workflow = _create_workflow(client)

            response = client.put(
                f"/api/v1/workflows/{workflow['id']}",
                json={"status": "PUBLISHED"},
            )
            detail_response = client.get(f"/api/v1/workflows/{workflow['id']}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["status"], "PUBLISHED")
        self.assertEqual(detail_response.status_code, 200)
        detail = detail_response.json()["data"]
        self.assertEqual(detail["status"], "PUBLISHED")
        self.assertEqual([node["nodeKey"] for node in detail["nodes"]], ["start", "end"])
        self.assertEqual(detail["edges"][0]["sourceNodeKey"], "start")
        self.assertEqual(detail["edges"][0]["targetNodeKey"], "end")


def _create_workflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": "Publish shell workflow",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "output"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
