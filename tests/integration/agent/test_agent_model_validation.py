from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class AgentModelValidationTest(unittest.TestCase):
    def test_create_rejects_missing_model_config(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/agents",
                json={
                    "name": f"Invalid Agent {time.time_ns()}",
                    "modelConfigId": 999999,
                    "temperature": 0.7,
                    "maxTokens": 2048,
                    "maxContextTurns": 10,
                },
            )

            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json()["message"], "Model config not found or disabled")

    def test_create_rejects_disabled_model_config(self) -> None:
        model_id = _seed_model(enabled=False)

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/agents",
                json={
                    "name": f"Disabled Model Agent {time.time_ns()}",
                    "modelConfigId": model_id,
                    "temperature": 0.7,
                    "maxTokens": 2048,
                    "maxContextTurns": 10,
                },
            )

            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json()["message"], "Model config not found or disabled")


def _seed_model(enabled: bool) -> int:
    initialise_database()
    register_baseline_tables()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    now = datetime.now()
    with get_session_factory()() as session:
        provider_id = session.execute(
            provider.insert().values(
                name=f"Agent Validation Provider {time.time_ns()}",
                type="OPENAI",
                base_url="mock://success",
                auth_config={"api_key": "sk-test"},
                description="",
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        model_id = session.execute(
            model_config.insert().values(
                provider_id=provider_id,
                name="Validation Model",
                model_id="validation-model",
                context_size=4096,
                extra_params={},
                enabled=enabled,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(model_id)


if __name__ == "__main__":
    unittest.main()
