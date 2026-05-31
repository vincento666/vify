from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class ChatSessionCrudTest(unittest.TestCase):
    def test_create_list_messages_and_delete_session(self) -> None:
        agent_id = _seed_agent()

        with TestClient(app) as client:
            create_response = client.post("/api/v1/chat/sessions", json={"agentId": agent_id})
            self.assertEqual(create_response.status_code, 200)
            created = create_response.json()["data"]
            self.assertEqual(created["agentId"], agent_id)
            self.assertEqual(created["status"], "ACTIVE")

            _seed_message(created["id"], role="user", content="hello")

            list_response = client.get("/api/v1/chat/sessions", params={"page": 1, "pageSize": 20})
            self.assertEqual(list_response.status_code, 200)
            page = list_response.json()["data"]
            self.assertTrue(any(item["id"] == created["id"] for item in page["list"]))

            messages_response = client.get(
                f"/api/v1/chat/sessions/{created['id']}/messages",
                params={"page": 1, "pageSize": 20},
            )
            self.assertEqual(messages_response.status_code, 200)
            messages = messages_response.json()["data"]
            self.assertEqual(messages["list"][0]["role"], "user")
            self.assertEqual(messages["list"][0]["content"], "hello")

            delete_response = client.delete(f"/api/v1/chat/sessions/{created['id']}")
            self.assertEqual(delete_response.status_code, 200)
            self.assertIsNone(delete_response.json()["data"])

            after_delete = client.get("/api/v1/chat/sessions", params={"page": 1, "pageSize": 20})
            self.assertFalse(
                any(item["id"] == created["id"] for item in after_delete.json()["data"]["list"])
            )

    def test_create_session_rejects_missing_agent(self) -> None:
        with TestClient(app) as client:
            response = client.post("/api/v1/chat/sessions", json={"agentId": 987654321})

        self.assertEqual(response.status_code, 404)


def _seed_agent() -> int:
    initialise_database()
    register_baseline_tables()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    agent = Base.metadata.tables["agent"]
    now = datetime.now()
    with get_session_factory()() as session:
        provider_id = session.execute(
            provider.insert().values(
                name=f"Chat Provider {time.time_ns()}",
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
                name="Chat Model",
                model_id="chat-model",
                context_size=4096,
                extra_params={},
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        agent_id = session.execute(
            agent.insert().values(
                name=f"Chat Agent {time.time_ns()}",
                description="",
                system_prompt="",
                model_config_id=model_id,
                temperature=0.7,
                max_tokens=2048,
                max_context_turns=10,
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(agent_id)


def _seed_message(session_id: int, role: str, content: str) -> int:
    initialise_database()
    register_baseline_tables()
    chat_message = Base.metadata.tables["chat_message"]
    now = datetime.now()
    with get_session_factory()() as session:
        message_id = session.execute(
            chat_message.insert().values(
                session_id=session_id,
                role=role,
                content=content,
                tokens=1,
                finish_reason="",
                latency_ms=0,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(message_id)


if __name__ == "__main__":
    unittest.main()
