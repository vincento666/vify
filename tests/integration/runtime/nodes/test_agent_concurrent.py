from __future__ import annotations

import time
import unittest
from datetime import datetime

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app

from ._helpers import (
    assert_completed_node_runs,
    assert_wave_started_before_first_completion,
    create_fanout_workflow,
    wait_for_runtime_result,
)


class RuntimeV2AgentConcurrentTest(unittest.TestCase):
    def test_three_agent_nodes_in_same_frontier_wave_keep_outputs_and_events_isolated(self) -> None:
        node_keys = {"agent_a", "agent_b", "agent_c"}
        agent_id = _seed_direct_agent()
        with TestClient(app) as client:
            workflow = create_fanout_workflow(
                client,
                name_prefix="217.2 Agent fanout",
                nodes=[
                    _agent_node("agent_a", agent_id, "A"),
                    _agent_node("agent_b", agent_id, "B"),
                    _agent_node("agent_c", agent_id, "C"),
                ],
                output_template="{{agent_a.agentAnswer}}|{{agent_b.agentAnswer}}|{{agent_c.agentAnswer}}",
            )
            started = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"ticket": "T-2172"}},
            ).json()["data"]
            terminal = wait_for_runtime_result(client, started["resultRef"])
            events = client.get(started["eventsRef"]).json()["data"]["list"]
            nodes = client.get(started["nodesRef"]).json()["data"]["list"]

        final = terminal["output"]["final"]
        self.assertIn("agent A handles T-2172", final)
        self.assertIn("agent B handles T-2172", final)
        self.assertIn("agent C handles T-2172", final)
        assert_completed_node_runs(nodes, node_keys, "AGENT_CALL")
        assert_wave_started_before_first_completion(events, node_keys)


def _seed_direct_agent() -> int:
    initialise_database()
    register_baseline_tables()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    agent = Base.metadata.tables["agent"]
    now = datetime.now()
    with get_session_factory()() as session:
        provider_id = session.execute(
            provider.insert().values(
                name=f"217.2 Agent provider {time.time_ns()}",
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
                name="217.2 Agent model",
                model_id="agent-call-model",
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
                name=f"217.2 Agent {time.time_ns()}",
                description="",
                system_prompt="Echo the request.",
                model_config_id=model_id,
                temperature=0.2,
                max_tokens=512,
                max_context_turns=10,
                tool_policies={},
                knowledge_base_id=None,
                workflow_id=None,
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(agent_id)


def _agent_node(node_key: str, agent_id: int, suffix: str) -> dict[str, object]:
    return {
        "nodeKey": node_key,
        "type": "AGENT_CALL",
        "name": f"Agent {suffix}",
        "config": {
            "targetAgentId": agent_id,
            "inputMappings": [
                {
                    "name": "message",
                    "valueMode": "reference",
                    "value": f"agent {suffix} handles {{{{start.ticket}}}}",
                    "required": True,
                }
            ],
            "outputMappings": [{"source": "answer", "target": "agentAnswer"}],
            "timeoutMs": 30000,
            "maxDepth": 3,
            "outputParameters": [
                {"name": "agentAnswer", "type": "string"},
                {"name": "sessionId", "type": "number"},
                {"name": "status", "type": "string"},
                {"name": "latencyMs", "type": "number"},
                {"name": "mappedInputSummary", "type": "object"},
                {"name": "mappedOutputSummary", "type": "object"},
                {"name": "toolCalls", "type": "array"},
                {"name": "error", "type": "string"},
            ],
        },
    }


if __name__ == "__main__":
    unittest.main()
