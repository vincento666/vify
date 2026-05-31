import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class WorkflowGraphCrudTest(unittest.TestCase):
    def test_create_detail_update_and_delete_workflow_graph(self) -> None:
        name = f"Workflow CRUD {time.time_ns()}"

        with TestClient(app) as client:
            create_response = client.post(
                "/api/v1/workflows",
                json={
                    "name": name,
                    "description": "created from test",
                    "nodes": [
                        {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                        {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "answer"}},
                    ],
                    "edges": [{"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None}],
                },
            )

            self.assertEqual(create_response.status_code, 200)
            created = create_response.json()["data"]
            self.assertEqual(created["name"], name)
            self.assertEqual(created["status"], "DRAFT")
            self.assertEqual([node["nodeKey"] for node in created["nodes"]], ["start", "end"])
            self.assertEqual(created["edges"][0]["targetNodeKey"], "end")

            list_response = client.get("/api/v1/workflows", params={"page": 1, "pageSize": 20})
            self.assertTrue(any(item["id"] == created["id"] for item in list_response.json()["data"]["list"]))

            detail_response = client.get(f"/api/v1/workflows/{created['id']}")
            self.assertEqual(detail_response.status_code, 200)
            self.assertEqual(detail_response.json()["data"]["nodes"][1]["config"]["outputVariable"], "answer")

            update_response = client.put(
                f"/api/v1/workflows/{created['id']}",
                json={
                    "name": name,
                    "description": "updated from test",
                    "status": "PUBLISHED",
                    "nodes": [
                        {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                        {"nodeKey": "llm", "type": "LLM", "name": "Answer", "config": {"outputVariable": "answer"}},
                        {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "answer"}},
                    ],
                    "edges": [
                        {"sourceNodeKey": "start", "targetNodeKey": "llm", "condition": None},
                        {"sourceNodeKey": "llm", "targetNodeKey": "end", "condition": None},
                    ],
                },
            )
            self.assertEqual(update_response.status_code, 200)
            updated = update_response.json()["data"]
            self.assertEqual(updated["description"], "updated from test")
            self.assertEqual(updated["status"], "PUBLISHED")
            self.assertEqual([node["nodeKey"] for node in updated["nodes"]], ["start", "llm", "end"])

            delete_response = client.delete(f"/api/v1/workflows/{created['id']}")
            self.assertEqual(delete_response.status_code, 200)
            self.assertIsNone(delete_response.json()["data"])

            missing_response = client.get(f"/api/v1/workflows/{created['id']}")
            self.assertEqual(missing_response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
