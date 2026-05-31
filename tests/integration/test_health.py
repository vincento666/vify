import unittest

from fastapi.testclient import TestClient

from app.main import app


class HealthRouteTest(unittest.TestCase):
    def test_health_returns_success_envelope(self) -> None:
        response = TestClient(app).get("/api/v1/health")

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
                    },
                },
            },
        )


if __name__ == "__main__":
    unittest.main()
