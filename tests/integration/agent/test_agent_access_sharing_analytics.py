from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class AgentAccessSharingAnalyticsContractTest(unittest.TestCase):
    def test_agent_access_sharing_catalog_and_analytics_shell_persist(self) -> None:
        model_id = _seed_model()
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/agents",
                json={
                    "name": f"Agent Access Sharing {time.time_ns()}",
                    "systemPrompt": "access shell",
                    "modelConfigId": model_id,
                    "temperature": 0.2,
                    "maxTokens": 512,
                    "maxContextTurns": 4,
                    "toolIds": [],
                    "access": {"mode": "PRIVATE", "owners": ["vincento"], "readonly": False},
                    "sharing": {"enabled": True, "publicToken": "pub-test"},
                    "catalog": {"visible": True, "category": "support"},
                    "analytics": {"usage": 3, "latencyMs": 120, "errors": 0},
                },
            )
            self.assertEqual(response.status_code, 200)
            agent = response.json()["data"]
            self.assertEqual(agent["access"]["mode"], "PRIVATE")
            self.assertEqual(agent["sharing"]["publicToken"], "pub-test")
            self.assertTrue(agent["catalog"]["visible"])
            self.assertEqual(agent["analytics"]["usage"], 3)


if __name__ == "__main__":
    unittest.main()


def _seed_model() -> int:
    initialise_database()
    register_baseline_tables()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    now = datetime.now()
    with get_session_factory()() as session:
        provider_id = session.execute(
            provider.insert().values(
                name=f"Agent Access Provider {time.time_ns()}",
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
                name="Agent Access Model",
                model_id="agent-access-model",
                context_size=4096,
                extra_params={},
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(model_id)
