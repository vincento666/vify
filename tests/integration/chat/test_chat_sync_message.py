from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class ChatSyncMessageTest(unittest.TestCase):
    def test_send_sync_message_persists_user_and_assistant_messages(self) -> None:
        agent_id = _seed_agent(system_prompt="You answer briefly.")

        with TestClient(app) as client:
            session_id = client.post("/api/v1/chat/sessions", json={"agentId": agent_id}).json()["data"]["id"]

            response = client.post(
                f"/api/v1/chat/sessions/{session_id}/messages",
                json={"content": "hello sync", "stream": False},
            )

            self.assertEqual(response.status_code, 200)
            data = response.json()["data"]
            self.assertEqual(data["userMessage"]["content"], "hello sync")
            self.assertEqual(data["assistantMessage"]["role"], "assistant")
            self.assertEqual(data["assistantMessage"]["content"], "Echo: hello sync")

            messages = client.get(f"/api/v1/chat/sessions/{session_id}/messages").json()["data"]["list"]
            self.assertEqual([message["role"] for message in messages], ["user", "assistant"])
            self.assertEqual(messages[1]["content"], "Echo: hello sync")


def _seed_agent(system_prompt: str = "") -> int:
    initialise_database()
    register_baseline_tables()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    agent = Base.metadata.tables["agent"]
    now = datetime.now()
    with get_session_factory()() as session:
        provider_id = session.execute(
            provider.insert().values(
                name=f"Sync Chat Provider {time.time_ns()}",
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
                name="Sync Chat Model",
                model_id="sync-chat-model",
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
                name=f"Sync Chat Agent {time.time_ns()}",
                description="",
                system_prompt=system_prompt,
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


if __name__ == "__main__":
    unittest.main()
