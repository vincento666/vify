from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class ChatWorkflowFailureTest(unittest.TestCase):
    def test_workflow_bound_agent_surfaces_execution_error_when_graph_is_invalid(self) -> None:
        with TestClient(app) as client:
            workflow = client.post(
                "/api/v1/workflows",
                json={
                    "name": f"Broken chat workflow {time.time_ns()}",
                    "description": "",
                    "nodes": [{"nodeKey": "llm", "type": "LLM", "name": "No start", "config": {}}],
                    "edges": [],
                },
            ).json()["data"]
            agent_id = _seed_agent(workflow_id=int(workflow["id"]))
            session_id = client.post("/api/v1/chat/sessions", json={"agentId": agent_id}).json()["data"]["id"]

            turn = client.post(
                f"/api/v1/chat/sessions/{session_id}/messages",
                json={"content": "hello", "stream": False},
            ).json()["data"]

        self.assertEqual(
            turn["assistantMessage"]["content"],
            "Workflow error: Workflow START node not found",
        )


def _seed_agent(workflow_id: int) -> int:
    initialise_database()
    register_baseline_tables()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    agent = Base.metadata.tables["agent"]
    now = datetime.now()
    with get_session_factory()() as session:
        provider_id = session.execute(
            provider.insert().values(
                name=f"Workflow Failure Provider {time.time_ns()}",
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
                name="Workflow Failure Model",
                model_id="workflow-failure-model",
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
                name=f"Workflow Failure Agent {time.time_ns()}",
                description="",
                system_prompt="",
                model_config_id=model_id,
                temperature=0.7,
                max_tokens=2048,
                max_context_turns=10,
                knowledge_base_id=None,
                workflow_id=workflow_id,
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
