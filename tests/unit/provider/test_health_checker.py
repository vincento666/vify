import time
import unittest

from fastapi.testclient import TestClient

from app.modules.provider.domain.health import ProviderHealthChecker
from app.main import app


class ProviderHealthCheckerTest(unittest.TestCase):
    def test_health_checker_updates_enabled_provider_status(self) -> None:
        with TestClient(app) as client:
            created = client.post(
                "/api/v1/providers",
                json={
                    "name": f"Health Provider {time.time_ns()}",
                    "type": "OPENAI",
                    "baseUrl": "mock://success",
                    "authConfig": {"api_key": "sk-test"},
                },
            ).json()["data"]

            checked = ProviderHealthChecker().check_once()

            self.assertGreaterEqual(checked, 1)
            detail = client.get(f"/api/v1/providers/{created['id']}").json()["data"]
            self.assertEqual(detail["health"]["status"], "UP")
            self.assertEqual(detail["health"]["latencyMs"], 0)


if __name__ == "__main__":
    unittest.main()
