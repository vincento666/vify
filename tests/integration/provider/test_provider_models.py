from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory
from app.main import app


class ProviderModelsContractTest(unittest.TestCase):
    def test_provider_detail_includes_model_configs(self) -> None:
        provider_name = f"Model Provider {time.time_ns()}"

        with TestClient(app) as client:
            created = client.post(
                "/api/v1/providers",
                json={
                    "name": provider_name,
                    "type": "OPENAI",
                    "baseUrl": "https://api.example.com/v1",
                    "authConfig": {"api_key": "sk-test"},
                },
            ).json()["data"]

            model_config = Base.metadata.tables["model_config"]
            now = datetime.now()
            with get_session_factory()() as session:
                session.execute(
                    model_config.insert().values(
                        provider_id=created["id"],
                        name="GPT-4o",
                        model_id="gpt-4o",
                        context_size=128000,
                        extra_params={},
                        enabled=True,
                        deleted=False,
                        created_at=now,
                        updated_at=now,
                    )
                )
                session.commit()

            detail_response = client.get(f"/api/v1/providers/{created['id']}")
            self.assertEqual(detail_response.status_code, 200)
            models = detail_response.json()["data"]["models"]
            self.assertEqual(models[0]["modelId"], "gpt-4o")
            self.assertTrue(models[0]["enabled"])


if __name__ == "__main__":
    unittest.main()
