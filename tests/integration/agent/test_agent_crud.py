from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class AgentCrudContractTest(unittest.TestCase):
    def test_create_list_update_delete_agent(self) -> None:
        agent_name = f"Agent {time.time_ns()}"
        model_id = _seed_model()

        with TestClient(app) as client:
            create_response = client.post(
                "/api/v1/agents",
                json={
                    "name": agent_name,
                    "description": "created from test",
                    "systemPrompt": "You are helpful.",
                    "modelConfigId": model_id,
                    "temperature": 0.7,
                    "maxTokens": 2048,
                    "maxContextTurns": 10,
                    "toolIds": [],
                },
            )
            self.assertEqual(create_response.status_code, 200)
            created = create_response.json()["data"]
            self.assertEqual(created["name"], agent_name)
            self.assertEqual(created["modelConfigId"], model_id)
            self.assertEqual(created["toolIds"], [])

            list_response = client.get("/api/v1/agents", params={"page": 1, "pageSize": 20})
            self.assertEqual(list_response.status_code, 200)
            page = list_response.json()["data"]
            self.assertTrue(any(item["id"] == created["id"] for item in page["list"]))

            update_response = client.put(
                f"/api/v1/agents/{created['id']}",
                json={
                    "name": agent_name,
                    "description": "updated from test",
                    "systemPrompt": "You are stricter.",
                    "modelConfigId": model_id,
                    "temperature": 0.2,
                    "maxTokens": 1024,
                    "maxContextTurns": 4,
                },
            )
            self.assertEqual(update_response.status_code, 200)
            updated = update_response.json()["data"]
            self.assertEqual(updated["description"], "updated from test")
            self.assertEqual(updated["temperature"], 0.2)

            delete_response = client.delete(f"/api/v1/agents/{created['id']}")
            self.assertEqual(delete_response.status_code, 200)
            self.assertIsNone(delete_response.json()["data"])


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
                name=f"Agent CRUD Provider {time.time_ns()}",
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
                name="Agent CRUD Model",
                model_id="agent-crud-model",
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
