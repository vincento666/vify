import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class ProviderConnectionContractTest(unittest.TestCase):
    def test_test_connection_route_returns_frontend_shape(self) -> None:
        with TestClient(app) as client:
            created = client.post(
                "/api/v1/providers",
                json={
                    "name": f"Connection Provider {time.time_ns()}",
                    "type": "OPENAI",
                    "baseUrl": "mock://success",
                    "authConfig": {"api_key": "sk-test"},
                },
            ).json()["data"]

            response = client.post(f"/api/v1/providers/{created['id']}/test-connection", json={})

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["data"]["success"], True)
            self.assertEqual(response.json()["data"]["modelCount"], 2)
            self.assertIsNotNone(response.json()["data"]["latencyMs"])


if __name__ == "__main__":
    unittest.main()
