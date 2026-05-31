import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class ChatflowPublishStatusTest(unittest.TestCase):
    def test_chatflow_status_update_stays_in_chatflow_scope(self) -> None:
        with TestClient(app) as client:
            create_response = client.post(
                "/api/v1/chatflows",
                json={
                    "name": f"Chatflow publish {time.time_ns()}",
                    "description": "",
                    "nodes": [
                        {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                        {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "output"}},
                    ],
                    "edges": [{"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None}],
                },
            )
            chatflow = create_response.json()["data"]
            update_response = client.put(f"/api/v1/chatflows/{chatflow['id']}", json={"status": "PUBLISHED"})
            workflow_detail = client.get(f"/api/v1/workflows/{chatflow['id']}")
            chatflow_detail = client.get(f"/api/v1/chatflows/{chatflow['id']}")

        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["data"]["status"], "PUBLISHED")
        self.assertEqual(workflow_detail.status_code, 404)
        self.assertEqual(chatflow_detail.json()["data"]["status"], "PUBLISHED")


if __name__ == "__main__":
    unittest.main()
