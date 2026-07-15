import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class ProviderCrudContractTest(unittest.TestCase):
    def test_blank_api_key_is_not_reported_as_configured(self) -> None:
        provider_name = f"Blank auth provider {time.time_ns()}"

        with TestClient(app) as client:
            create_response = client.post(
                "/api/v1/providers",
                json={
                    "name": provider_name,
                    "type": "OPENAI_COMPATIBLE",
                    "baseUrl": "https://api.example.com/v1",
                    "authConfig": {"api_key": ""},
                },
            )
            self.assertEqual(create_response.status_code, 200)
            created = create_response.json()["data"]
            self.assertFalse(created["authConfigured"])

            delete_response = client.delete(f"/api/v1/providers/{created['id']}")
            self.assertEqual(delete_response.status_code, 200)

    def test_create_list_update_delete_provider(self) -> None:
        provider_name = f"Provider {time.time_ns()}"

        with TestClient(app) as client:
            create_response = client.post(
                "/api/v1/providers",
                json={
                    "name": provider_name,
                    "type": "OPENAI",
                    "baseUrl": "https://api.example.com/v1",
                    "description": "created from test",
                    "authConfig": {"api_key": "sk-test"},
                },
            )
            self.assertEqual(create_response.status_code, 200)
            created = create_response.json()["data"]
            self.assertEqual(created["name"], provider_name)
            self.assertEqual(created["baseUrl"], "https://api.example.com/v1")
            self.assertTrue(created["authConfigured"])
            self.assertEqual(created["models"], [])
            self.assertIsNone(created["health"])

            list_response = client.get("/api/v1/providers", params={"page": 1, "pageSize": 20})
            self.assertEqual(list_response.status_code, 200)
            page = list_response.json()["data"]
            self.assertGreaterEqual(page["total"], 1)
            self.assertTrue(any(item["id"] == created["id"] for item in page["list"]))

            update_response = client.put(
                f"/api/v1/providers/{created['id']}",
                json={
                    "description": "updated from test",
                    "enabled": False,
                },
            )
            self.assertEqual(update_response.status_code, 200)
            updated = update_response.json()["data"]
            self.assertEqual(updated["description"], "updated from test")
            self.assertFalse(updated["enabled"])

            delete_response = client.delete(f"/api/v1/providers/{created['id']}")
            self.assertEqual(delete_response.status_code, 200)
            self.assertIsNone(delete_response.json()["data"])

            detail_response = client.get(f"/api/v1/providers/{created['id']}")
            self.assertEqual(detail_response.status_code, 404)
            self.assertEqual(detail_response.json()["message"], "Provider not found")


if __name__ == "__main__":
    unittest.main()
