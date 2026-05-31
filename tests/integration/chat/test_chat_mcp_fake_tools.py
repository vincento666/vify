from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class ChatMcpFakeToolsTest(unittest.TestCase):
    def test_tool_bound_agent_mentions_fake_mcp_tool_names_in_mock_result(self) -> None:
        agent_id = _seed_tool_bound_agent(endpoint="mock://tools")

        with TestClient(app) as client:
            session_id = client.post("/api/v1/chat/sessions", json={"agentId": agent_id}).json()["data"]["id"]
            turn = client.post(
                f"/api/v1/chat/sessions/{session_id}/messages",
                json={"content": "please use tool", "stream": False},
            ).json()["data"]

        self.assertEqual(
            turn["assistantMessage"]["content"],
            "Tool mock (lookup_order, refund_order): please use tool",
        )


def _seed_tool_bound_agent(endpoint: str) -> int:
    initialise_database()
    register_baseline_tables()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    agent = Base.metadata.tables["agent"]
    mcp_server = Base.metadata.tables["mcp_server"]
    agent_tool = Base.metadata.tables["agent_tool"]
    now = datetime.now()
    with get_session_factory()() as session:
        provider_id = session.execute(
            provider.insert().values(
                name=f"Fake Tool Chat Provider {time.time_ns()}",
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
                name="Fake Tool Chat Model",
                model_id="fake-tool-chat-model",
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
                name=f"Fake Tool Chat Agent {time.time_ns()}",
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
        server_id = session.execute(
            mcp_server.insert().values(
                name=f"Fake Tool Chat MCP {time.time_ns()}",
                endpoint=endpoint,
                description="",
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.execute(
            agent_tool.insert().values(
                agent_id=agent_id,
                mcp_server_id=server_id,
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()
    return int(agent_id)


if __name__ == "__main__":
    unittest.main()
