from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class AgentMemoryVariablesContractTest(unittest.TestCase):
    def test_agent_variables_memory_persist_and_inject_into_chat_runtime(self) -> None:
        model_id = _seed_model()
        agent_name = f"Agent Variable Memory {time.time_ns()}"

        with TestClient(app) as client:
            create_response = client.post(
                "/api/v1/agents",
                json={
                    "name": agent_name,
                    "description": "variable runtime contract",
                    "systemPrompt": "Answer with the runtime context when useful.",
                    "modelConfigId": model_id,
                    "temperature": 0.2,
                    "maxTokens": 512,
                    "maxContextTurns": 4,
                    "toolIds": [],
                    "variables": [
                        {
                            "name": "customer_name",
                            "type": "string",
                            "defaultValue": "Ada",
                            "required": True,
                            "description": "current customer name",
                        },
                        {
                            "name": "tier",
                            "type": "string",
                            "defaultValue": "gold",
                            "required": False,
                            "description": "membership tier",
                        },
                    ],
                    "memory": {
                        "profile": "prefers concise Chinese replies",
                        "last_order": "A-100",
                    },
                },
            )
            self.assertEqual(create_response.status_code, 200)
            created = create_response.json()["data"]
            self.assertEqual(created["variables"][0]["name"], "customer_name")
            self.assertEqual(created["variables"][0]["defaultValue"], "Ada")
            self.assertEqual(created["memory"]["last_order"], "A-100")

            detail_response = client.get(f"/api/v1/agents/{created['id']}")
            self.assertEqual(detail_response.status_code, 200)
            detail = detail_response.json()["data"]
            self.assertEqual(detail["variables"][1]["name"], "tier")
            self.assertEqual(detail["memory"]["profile"], "prefers concise Chinese replies")

            session_response = client.post("/api/v1/chat/sessions", json={"agentId": created["id"]})
            self.assertEqual(session_response.status_code, 200)
            session_id = session_response.json()["data"]["id"]
            message_response = client.post(
                f"/api/v1/chat/sessions/{session_id}/messages",
                json={
                    "content": "请确认当前客户是谁",
                    "stream": False,
                    "variables": {"customer_name": "Vincent"},
                },
            )
            self.assertEqual(message_response.status_code, 200)
            assistant = message_response.json()["data"]["assistantMessage"]["content"]
            self.assertIn("customer_name=Vincent", assistant)
            self.assertIn("tier=gold", assistant)
            self.assertIn("last_order=A-100", assistant)

    def test_invalid_agent_variable_name_is_rejected(self) -> None:
        model_id = _seed_model()
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/agents",
                json={
                    "name": f"Agent Invalid Variable {time.time_ns()}",
                    "systemPrompt": "",
                    "modelConfigId": model_id,
                    "temperature": 0.2,
                    "maxTokens": 512,
                    "maxContextTurns": 4,
                    "toolIds": [],
                    "variables": [{"name": "bad-name", "type": "string", "defaultValue": ""}],
                },
            )
            self.assertEqual(response.status_code, 400)
            self.assertIn("Invalid Agent variable name", response.json()["message"])


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
                name=f"Agent Variable Provider {time.time_ns()}",
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
                name="Agent Variable Model",
                model_id="agent-variable-model",
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
