import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class KnowledgeBaseCrudTest(unittest.TestCase):
    def test_create_list_detail_update_and_delete_knowledge_base(self) -> None:
        name = f"Knowledge CRUD {time.time_ns()}"

        with TestClient(app) as client:
            create_response = client.post(
                "/api/v1/knowledge-bases",
                json={"name": name, "description": "created from test"},
            )
            self.assertEqual(create_response.status_code, 200)
            created = create_response.json()["data"]
            self.assertEqual(created["name"], name)
            self.assertEqual(created["enabled"], 1)

            list_response = client.get("/api/v1/knowledge-bases", params={"page": 1, "pageSize": 20})
            self.assertTrue(any(item["id"] == created["id"] for item in list_response.json()["data"]["list"]))

            detail_response = client.get(f"/api/v1/knowledge-bases/{created['id']}")
            self.assertEqual(detail_response.json()["data"]["description"], "created from test")

            update_response = client.put(
                f"/api/v1/knowledge-bases/{created['id']}",
                json={"name": name, "description": "updated from test", "enabled": 0},
            )
            self.assertEqual(update_response.status_code, 200)
            updated = update_response.json()["data"]
            self.assertEqual(updated["description"], "updated from test")
            self.assertEqual(updated["enabled"], 0)

            delete_response = client.delete(f"/api/v1/knowledge-bases/{created['id']}")
            self.assertEqual(delete_response.status_code, 200)
            self.assertIsNone(delete_response.json()["data"])

            missing_response = client.get(f"/api/v1/knowledge-bases/{created['id']}")
            self.assertEqual(missing_response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
