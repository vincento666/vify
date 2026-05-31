from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app
from app.modules.knowledge.domain.service import KnowledgeBaseService
from app.modules.knowledge.infra.repository import KnowledgeBaseRepository


class ChatProviderBackedPathsTest(unittest.TestCase):
    def test_direct_chat_uses_agent_model_provider_instead_of_echo(self) -> None:
        agent_id = _seed_agent(system_prompt="Answer briefly.")

        with TestClient(app) as client:
            session_id = client.post("/api/v1/chat/sessions", json={"agentId": agent_id}).json()["data"]["id"]
            turn = client.post(
                f"/api/v1/chat/sessions/{session_id}/messages",
                json={"content": "hello direct", "stream": False},
            ).json()["data"]

        content = turn["assistantMessage"]["content"]
        self.assertIn("LLM mock:", content)
        self.assertIn("hello direct", content)
        self.assertNotIn("Echo:", content)

    def test_knowledge_chat_uses_llm_with_retrieved_context(self) -> None:
        kb_id = _seed_knowledge_base_with_document()
        agent_id = _seed_agent(knowledge_base_id=kb_id)

        with TestClient(app) as client:
            session_id = client.post("/api/v1/chat/sessions", json={"agentId": agent_id}).json()["data"]["id"]
            turn = client.post(
                f"/api/v1/chat/sessions/{session_id}/messages",
                json={"content": "reset password", "stream": False},
            ).json()["data"]

        content = turn["assistantMessage"]["content"]
        self.assertIn("LLM mock:", content)
        self.assertIn("How to reset password", content)
        self.assertIn("References:", content)
        self.assertNotIn("RAG mock:", content)

    def test_workflow_chat_uses_llm_to_finalize_workflow_output(self) -> None:
        with TestClient(app) as client:
            workflow = _create_linear_workflow(client)
            agent_id = _seed_agent(workflow_id=int(workflow["id"]))
            session_id = client.post("/api/v1/chat/sessions", json={"agentId": agent_id}).json()["data"]["id"]
            turn = client.post(
                f"/api/v1/chat/sessions/{session_id}/messages",
                json={"content": "reset password", "stream": False},
            ).json()["data"]

        content = turn["assistantMessage"]["content"]
        self.assertIn("LLM mock:", content)
        self.assertIn("reset password", content)
        self.assertNotIn("Workflow mock:", content)

    def test_tool_chat_uses_llm_tool_calling_path_by_default(self) -> None:
        agent_id = _seed_agent(tool_bound=True)

        with TestClient(app) as client:
            session_id = client.post("/api/v1/chat/sessions", json={"agentId": agent_id}).json()["data"]["id"]
            turn = client.post(
                f"/api/v1/chat/sessions/{session_id}/messages",
                json={"content": "where is order A-100?", "stream": False},
            ).json()["data"]

        content = turn["assistantMessage"]["content"]
        self.assertIn("Tool answer:", content)
        self.assertIn("Order A-100 status: SHIPPED", content)
        self.assertNotIn("Tool mock:", content)


def _seed_agent(
    system_prompt: str = "",
    knowledge_base_id: int | None = None,
    workflow_id: int | None = None,
    tool_bound: bool = False,
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
                name=f"Provider backed {time.time_ns()}",
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
                name="Provider backed model",
                model_id="provider-backed-model",
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
                name=f"Provider backed agent {time.time_ns()}",
                description="",
                system_prompt=system_prompt,
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
        if tool_bound:
            server_id = session.execute(
                mcp_server.insert().values(
                    name=f"Provider backed MCP {time.time_ns()}",
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


def _seed_knowledge_base_with_document() -> int:
    kb_id = _seed_knowledge_base()
    content = b"Intro\n\nHow to reset password\n\nHow to contact support"
    with get_session_factory()() as session:
        service = KnowledgeBaseService(KnowledgeBaseRepository(session))
        document = service.upload_document(kb_id, "provider-backed-guide.txt", content)
        service.process_document(document["id"], content)
    return kb_id


def _seed_knowledge_base() -> int:
    initialise_database()
    register_baseline_tables()
    knowledge_base = Base.metadata.tables["knowledge_base"]
    now = datetime.now()
    with get_session_factory()() as session:
        kb_id = session.execute(
            knowledge_base.insert().values(
                name=f"Provider backed KB {time.time_ns()}",
                description="",
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(kb_id)


def _create_linear_workflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Provider backed workflow {time.time_ns()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "llm",
                    "type": "LLM",
                    "name": "Answer",
                    "config": {"prompt": "User: {{start.userMessage}}", "outputVariable": "answer"},
                },
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "answer"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "llm", "condition": None},
                {"sourceNodeKey": "llm", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
