from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app
from app.modules.knowledge.domain.service import KnowledgeBaseService
from app.modules.knowledge.infra.repository import KnowledgeBaseRepository


class ChatRagReferencesTest(unittest.TestCase):
    def test_knowledge_bound_agent_answer_uses_llm_and_includes_references(self) -> None:
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
        self.assertIn("References:", content)
        self.assertIn("How to reset password", content)
        self.assertNotIn("RAG mock:", content)


def _seed_knowledge_base_with_document() -> int:
    kb_id = _seed_knowledge_base()
    document_content = b"Intro\n\nHow to reset password\n\nHow to contact support"
    with get_session_factory()() as session:
        service = KnowledgeBaseService(KnowledgeBaseRepository(session))
        document = service.upload_document(kb_id, "chat-guide.txt", document_content)
        service.process_document(document["id"], document_content)
    return kb_id


def _seed_knowledge_base() -> int:
    initialise_database()
    register_baseline_tables()
    knowledge_base = Base.metadata.tables["knowledge_base"]
    now = datetime.now()
    with get_session_factory()() as session:
        knowledge_base_id = session.execute(
            knowledge_base.insert().values(
                name=f"Chat RAG KB {time.time_ns()}",
                description="",
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(knowledge_base_id)


def _seed_agent(knowledge_base_id: int) -> int:
    initialise_database()
    register_baseline_tables()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    agent = Base.metadata.tables["agent"]
    now = datetime.now()
    with get_session_factory()() as session:
        provider_id = session.execute(
            provider.insert().values(
                name=f"Chat RAG Provider {time.time_ns()}",
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
                name="Chat RAG Model",
                model_id="chat-rag-model",
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
                name=f"Chat RAG Agent {time.time_ns()}",
                description="",
                system_prompt="",
                model_config_id=model_id,
                temperature=0.7,
                max_tokens=2048,
                max_context_turns=10,
                knowledge_base_id=knowledge_base_id,
                workflow_id=None,
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
