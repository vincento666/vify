from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class AgentVersionContractTest(unittest.TestCase):
    def test_create_list_and_release_agent_version_snapshot(self) -> None:
        model_id = _seed_model()
        agent_name = f"Versioned Agent {time.time_ns()}"

        with TestClient(app) as client:
            created = client.post(
                "/api/v1/agents",
                json={
                    "name": agent_name,
                    "description": "version source",
                    "systemPrompt": "You are a versioned support agent.",
                    "modelConfigId": model_id,
                    "temperature": 0.3,
                    "maxTokens": 512,
                    "maxContextTurns": 6,
                    "openingMessage": "欢迎使用版本化 Agent。",
                    "suggestedQuestions": ["版本如何发布？"],
                    "toolIds": [],
                    "knowledgeBaseId": None,
                    "workflowId": None,
                },
            ).json()["data"]

            create_version_response = client.post(
                f"/api/v1/agents/{created['id']}/versions",
                json={"name": "release candidate"},
            )
            self.assertEqual(create_version_response.status_code, 200)
            version = create_version_response.json()["data"]

            self.assertEqual(version["versionNo"], 1)
            self.assertEqual(version["name"], "release candidate")
            self.assertFalse(version["released"])
            self.assertEqual(version["snapshot"]["name"], agent_name)
            self.assertEqual(version["snapshot"]["systemPrompt"], "You are a versioned support agent.")
            self.assertEqual(version["snapshot"]["openingMessage"], "欢迎使用版本化 Agent。")
            self.assertEqual(version["snapshot"]["suggestedQuestions"], ["版本如何发布？"])
            self.assertEqual(version["snapshot"]["modelConfigId"], model_id)
            self.assertEqual(version["snapshot"]["toolIds"], [])

            release_response = client.put(f"/api/v1/agents/{created['id']}/versions/{version['id']}/release")
            self.assertEqual(release_response.status_code, 200)
            released = release_response.json()["data"]
            self.assertTrue(released["released"])
            self.assertIsNotNone(released["releasedAt"])

            list_response = client.get(f"/api/v1/agents/{created['id']}/versions")
            self.assertEqual(list_response.status_code, 200)
            versions = list_response.json()["data"]
            self.assertEqual(len(versions["list"]), 1)
            self.assertEqual(versions["releasedVersionId"], released["id"])
            self.assertEqual(versions["latestVersionId"], released["id"])


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
                name=f"Agent Version Provider {time.time_ns()}",
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
                name="Agent Version Model",
                model_id="agent-version-model",
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
