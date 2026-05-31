from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class ChatBoundAgentHooksTest(unittest.TestCase):
    def test_knowledge_bound_agent_uses_llm_rag_path(self) -> None:
        agent_id = _seed_agent(knowledge_base_id=_seed_knowledge_base(), workflow_id=None)

        with TestClient(app) as client:
            session_id = client.post("/api/v1/chat/sessions", json={"agentId": agent_id}).json()["data"]["id"]
            turn = client.post(
                f"/api/v1/chat/sessions/{session_id}/messages",
                json={"content": "where is the policy?", "stream": False},
            ).json()["data"]

        self.assertEqual(turn["assistantMessage"]["content"], "LLM mock: where is the policy?")

    def test_workflow_bound_agent_uses_llm_workflow_path(self) -> None:
        agent_id = _seed_agent(knowledge_base_id=_seed_knowledge_base(), workflow_id=_seed_workflow())

        with TestClient(app) as client:
            session_id = client.post("/api/v1/chat/sessions", json={"agentId": agent_id}).json()["data"]["id"]
            turn = client.post(
                f"/api/v1/chat/sessions/{session_id}/messages",
                json={"content": "run onboarding", "stream": False},
            ).json()["data"]

        self.assertEqual(turn["assistantMessage"]["content"], "LLM mock: run onboarding")


def _seed_agent(knowledge_base_id: int | None, workflow_id: int | None) -> int:
    initialise_database()
    register_baseline_tables()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    agent = Base.metadata.tables["agent"]
    now = datetime.now()
    with get_session_factory()() as session:
        provider_id = session.execute(
            provider.insert().values(
                name=f"Hook Chat Provider {time.time_ns()}",
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
                name="Hook Chat Model",
                model_id="hook-chat-model",
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
                name=f"Hook Chat Agent {time.time_ns()}",
                description="",
                system_prompt="",
                model_config_id=model_id,
                temperature=0.7,
                max_tokens=2048,
                max_context_turns=10,
                knowledge_base_id=knowledge_base_id,
                workflow_id=workflow_id,
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(agent_id)


def _seed_knowledge_base() -> int:
    initialise_database()
    register_baseline_tables()
    knowledge_base = Base.metadata.tables["knowledge_base"]
    now = datetime.now()
    with get_session_factory()() as session:
        knowledge_base_id = session.execute(
            knowledge_base.insert().values(
                name=f"Hook KB {time.time_ns()}",
                description="",
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(knowledge_base_id)


def _seed_workflow() -> int:
    initialise_database()
    register_baseline_tables()
    workflow = Base.metadata.tables["workflow"]
    now = datetime.now()
    with get_session_factory()() as session:
        workflow_id = session.execute(
            workflow.insert().values(
                name=f"Hook Workflow {time.time_ns()}",
                description="",
                status="DRAFT",
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(workflow_id)


if __name__ == "__main__":
    unittest.main()
