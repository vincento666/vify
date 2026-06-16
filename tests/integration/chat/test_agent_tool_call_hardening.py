from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class AgentToolCallHardeningTest(unittest.TestCase):
    def test_tool_bound_agent_rejects_model_without_tool_calling_capability(self) -> None:
        agent_id = _seed_tool_bound_agent(supports_tool_calling=False)

        with TestClient(app) as client:
            session_id = client.post("/api/v1/chat/sessions", json={"agentId": agent_id}).json()["data"]["id"]
            response = client.post(
                f"/api/v1/chat/sessions/{session_id}/messages",
                json={"content": "where is order A-100?", "stream": False},
            )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("does not support tool calling", response.json()["message"])

    def test_tool_bound_agent_returns_normalized_tool_call_evidence(self) -> None:
        agent_id = _seed_tool_bound_agent(supports_tool_calling=True)

        with TestClient(app) as client:
            session_id = client.post("/api/v1/chat/sessions", json={"agentId": agent_id}).json()["data"]["id"]
            turn = client.post(
                f"/api/v1/chat/sessions/{session_id}/messages",
                json={"content": "where is order A-100?", "stream": False},
            ).json()["data"]
            debug = client.get(f"/api/v1/agents/{agent_id}/preview-runs/{session_id}/debug").json()["data"]

        tool_calls = turn["assistantMessage"]["toolCalls"]
        self.assertEqual(1, len(tool_calls))
        self.assertEqual("call_lookup_order", tool_calls[0]["callId"])
        self.assertEqual("lookup_order", tool_calls[0]["toolName"])
        self.assertEqual("success", tool_calls[0]["status"])
        self.assertIn("A-100", tool_calls[0]["argumentsSummary"])
        self.assertIn("SHIPPED", tool_calls[0]["contentSummary"])
        self.assertGreaterEqual(tool_calls[0]["latencyMs"], 0)
        self.assertTrue(any(node["id"] == "tool:lookup_order" for node in debug["nodes"]))
        self.assertEqual(tool_calls, debug["toolCalls"])

    def test_disabled_tool_policy_records_failure_evidence(self) -> None:
        agent_id = _seed_tool_bound_agent(
            supports_tool_calling=True,
            tool_policies={"lookup_order": {"enabled": False}},
        )

        with TestClient(app) as client:
            session_id = client.post("/api/v1/chat/sessions", json={"agentId": agent_id}).json()["data"]["id"]
            turn = client.post(
                f"/api/v1/chat/sessions/{session_id}/messages",
                json={"content": "where is order A-100?", "stream": False},
            ).json()["data"]

        tool_calls = turn["assistantMessage"]["toolCalls"]
        self.assertEqual(1, len(tool_calls))
        self.assertEqual("failed", tool_calls[0]["status"])
        self.assertIn("Tool disabled by policy", tool_calls[0]["errorMessage"])
        self.assertEqual("", tool_calls[0]["contentSummary"])


def _seed_tool_bound_agent(
    supports_tool_calling: bool,
    tool_policies: dict[str, object] | None = None,
) -> int:
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
                name=f"Tool hardening provider {time.time_ns()}",
                type="OPENAI_COMPATIBLE",
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
                name="Tool hardening model",
                model_id="tool-hardening-model",
                context_size=4096,
                extra_params={"supportsToolCalling": supports_tool_calling},
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        agent_id = session.execute(
            agent.insert().values(
                name=f"Tool hardening agent {time.time_ns()}",
                description="",
                system_prompt="",
                model_config_id=model_id,
                temperature=0.7,
                max_tokens=2048,
                max_context_turns=10,
                tool_policies=tool_policies or {},
                knowledge_base_id=None,
                workflow_id=None,
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        server_id = session.execute(
            mcp_server.insert().values(
                name=f"Tool hardening MCP {time.time_ns()}",
                endpoint="mock://tools",
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
