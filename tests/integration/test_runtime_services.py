import unittest

from fastapi.testclient import TestClient

from app.main import app


class RuntimeServicesTest(unittest.TestCase):
    def test_readyz_returns_component_statuses(self) -> None:
        response = TestClient(app).get("/readyz")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "code": 200,
                "message": "success",
                "data": {
                    "status": "UP",
                    "components": {
                        "app": "UP",
                        "database": "CONFIGURED",
                        "redis": "NOT_CONFIGURED",
                    },
                },
            },
        )

    def test_metrics_exposes_prometheus_text(self) -> None:
        response = TestClient(app).get("/metrics")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/plain", response.headers["content-type"])
        self.assertIn("hify_app_info", response.text)


if __name__ == "__main__":
    unittest.main()
