from datetime import datetime
import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.db_write import insert_and_get_id
from app.core.database import Base, get_session_factory
from app.main import app


class ProviderModelConnectivityContractTest(unittest.TestCase):
    def test_model_connectivity_route_runs_chat_probe(self) -> None:
        with TestClient(app) as client:
            created = client.post(
                "/api/v1/providers",
                json={
                    "name": f"Model Probe Provider {time.time_ns()}",
                    "type": "OPENAI_COMPATIBLE",
                    "baseUrl": "mock://success",
                    "authConfig": {"api_key": "sk-test"},
                },
            ).json()["data"]

            model_config_id = self._insert_model_config(created["id"], "probe-model")

            response = client.post(
                f"/api/v1/providers/{created['id']}/models/{model_config_id}/connectivity",
                json={},
            )

            self.assertEqual(response.status_code, 200)
            payload = response.json()["data"]
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["model"], "probe-model")
            self.assertEqual(payload["replyPreview"], "LLM mock: 1")
            self.assertIsInstance(payload["elapsedMs"], int)
            self.assertGreater(payload["usage"]["totalTokens"], 0)

    def test_model_connectivity_route_sanitizes_failed_probe_error(self) -> None:
        with TestClient(app) as client:
            created = client.post(
                "/api/v1/providers",
                json={
                    "name": f"Model Probe Failure Provider {time.time_ns()}",
                    "type": "OPENAI_COMPATIBLE",
                    "baseUrl": "https://api.example.com/v1",
                    "authConfig": {"api_key": "sk-secret-provider-key"},
                },
            ).json()["data"]
            model_config_id = self._insert_model_config(created["id"], "bad-model")

            with patch(
                "app.modules.provider.domain.model_connectivity."
                "ProviderBackedOpenAIChatClient.complete",
                side_effect=RuntimeError("HTTP 401 sk-secret-provider-key invalid"),
            ):
                response = client.post(
                    f"/api/v1/providers/{created['id']}/models/{model_config_id}/connectivity",
                    json={},
                )

            self.assertEqual(response.status_code, 200)
            payload = response.json()["data"]
            self.assertFalse(payload["ok"])
            self.assertIn("HTTP 401", payload["error"])
            self.assertNotIn("sk-secret-provider-key", response.text)

    def _insert_model_config(self, provider_id: int, model_id: str) -> int:
        model_config = Base.metadata.tables["model_config"]
        now = datetime.now()
        with get_session_factory()() as session:
            model_config_id = insert_and_get_id(
                session,
                model_config,
                {
                    "provider_id": provider_id,
                    "name": model_id,
                    "model_id": model_id,
                    "context_size": 128000,
                    "extra_params": {},
                    "enabled": True,
                    "deleted": False,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            session.commit()
        return model_config_id


if __name__ == "__main__":
    unittest.main()
