import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class SopRouterSessionGatewayProjectionTest(unittest.TestCase):
    def test_existing_session_message_endpoint_returns_gateway_projection(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/runtime-lab/sessions")
            session_id = created.json()["data"]["id"]
            response = client.post(
                f"/api/v1/runtime-lab/sessions/{session_id}/messages",
                json={"message": "我要退票", "idempotencyKey": f"session-path-{time.time_ns()}"},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["sessionId"], session_id)
        self.assertEqual(data["conversationId"], f"runtime-lab:{session_id}")
        self.assertEqual(data["currentSopId"], "refund_ticket")
        self.assertEqual(data["intent"], "refund_ticket")
        self.assertIsInstance(data["answer"], str)
        self.assertGreaterEqual(data["latencyMs"], 0)


if __name__ == "__main__":
    unittest.main()
