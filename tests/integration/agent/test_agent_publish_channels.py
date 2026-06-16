from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class AgentPublishChannelContractTest(unittest.TestCase):
    def test_publish_requires_released_version_and_can_unpublish(self) -> None:
        model_id = _seed_model()

        with TestClient(app) as client:
            agent = client.post(
                "/api/v1/agents",
                json={
                    "name": f"Publish Agent {time.time_ns()}",
                    "systemPrompt": "You are publishable.",
                    "modelConfigId": model_id,
                    "temperature": 0.2,
                    "maxTokens": 256,
                    "maxContextTurns": 4,
                    "toolIds": [],
                },
            ).json()["data"]
            version = client.post(f"/api/v1/agents/{agent['id']}/versions", json={"name": "candidate"}).json()["data"]

            blocked = client.post(
                f"/api/v1/agents/{agent['id']}/publishes",
                json={"versionId": version["id"], "channelType": "API"},
            )
            self.assertEqual(blocked.status_code, 400)

            released = client.put(f"/api/v1/agents/{agent['id']}/versions/{version['id']}/release").json()["data"]
            published_response = client.post(
                f"/api/v1/agents/{agent['id']}/publishes",
                json={"versionId": released["id"], "channelType": "API"},
            )
            self.assertEqual(published_response.status_code, 200)
            published = published_response.json()["data"]
            self.assertEqual(published["status"], "PUBLISHED")
            self.assertEqual(published["channelType"], "API")
            self.assertIn(f"/api/public/agents/{agent['id']}/versions/{released['id']}/chat", published["endpoint"])

            list_response = client.get(f"/api/v1/agents/{agent['id']}/publishes")
            self.assertEqual(list_response.status_code, 200)
            records = list_response.json()["data"]["list"]
            self.assertTrue(any(record["id"] == published["id"] for record in records))

            unpublished = client.put(
                f"/api/v1/agents/{agent['id']}/publishes/{published['id']}/unpublish",
            ).json()["data"]
            self.assertEqual(unpublished["status"], "UNPUBLISHED")


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
                name=f"Agent Publish Provider {time.time_ns()}",
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
                name="Agent Publish Model",
                model_id="agent-publish-model",
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
