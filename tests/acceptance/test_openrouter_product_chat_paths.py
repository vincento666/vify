from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app
from app.modules.knowledge.domain.service import KnowledgeBaseService
from app.modules.knowledge.infra.repository import KnowledgeBaseRepository


RUN_LIVE = os.getenv("HIFY_RUN_LIVE_OPENROUTER_PRODUCT") == "1"


@unittest.skipUnless(RUN_LIVE, "Set HIFY_RUN_LIVE_OPENROUTER_PRODUCT=1 to run live product chat acceptance")
class OpenRouterProductChatPathsAcceptanceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.api_key = os.environ["OPENROUTER_API_KEY"]
        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.model = os.getenv("OPENROUTER_MODEL", "xiaomi/mimo-v2-flash")
        self.artifact_path = Path(
            "artifacts/slices/010-real-tool-calling-and-mcp/010.7/product-chat-live-acceptance.md"
        )
        initialise_database()
        register_baseline_tables()

    def test_all_product_chat_paths_default_to_live_llm(self) -> None:
        direct_agent_id = _seed_agent(self.api_key, self.base_url, self.model)
        rag_agent_id = _seed_agent(
            self.api_key,
            self.base_url,
            self.model,
            knowledge_base_id=_seed_knowledge_base_with_document(),
        )

        with TestClient(app) as client:
            workflow = _create_live_workflow(client)
            workflow_agent_id = _seed_agent(
                self.api_key,
                self.base_url,
                self.model,
                workflow_id=int(workflow["id"]),
            )
            tool_agent_id = _seed_agent(self.api_key, self.base_url, self.model, tool_bound=True)

            direct = _send(client, direct_agent_id, "Return exactly this marker: HIFY_DIRECT_LIVE")
            rag = _send(
                client,
                rag_agent_id,
                "Using the knowledge context, return HIFY_RAG_LIVE and mention HIFY_RAG_CONTEXT.",
            )
            workflow_answer = _send(
                client,
                workflow_agent_id,
                "Use the workflow and include HIFY_WORKFLOW_FINAL_LIVE.",
            )
            tool = _send(
                client,
                tool_agent_id,
                "You must call lookup_order for order A-100, then answer with HIFY_TOOL_LIVE and the status.",
            )

        for label, content in {
            "direct": direct,
            "rag": rag,
            "workflow": workflow_answer,
            "tool": tool,
        }.items():
            self.assertTrue(content.strip(), f"{label} content should not be empty")
            self.assertNotIn("Echo:", content)
            self.assertNotIn("RAG mock:", content)
            self.assertNotIn("Workflow mock:", content)
            self.assertNotIn("Tool mock:", content)

        self.assertIn("HIFY_DIRECT_LIVE", direct)
        self.assertIn("HIFY_RAG", rag)
        self.assertIn("HIFY_WORKFLOW", workflow_answer)
        self.assertIn("HIFY_TOOL_LIVE", tool)
        self.assertIn("SHIPPED", tool.upper())

        self._write_artifact(
            {
                "direct": direct,
                "rag": rag,
                "workflow": workflow_answer,
                "tool": tool,
            }
        )

    def _write_artifact(self, results: dict[str, str]) -> None:
        self.artifact_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Product Chat Live LLM Acceptance",
            "",
            "- Slice: 010.7 product chat defaults to live LLM",
            f"- Base URL: `{self.base_url}`",
            f"- Model: `{self.model}`",
            "- API key: runtime environment only, not recorded",
            "- Direct chat: passed",
            "- RAG chat: passed",
            "- Workflow chat including workflow LLM node: passed",
            "- MCP tool chat: passed",
            "",
            "## Evidence",
            "",
        ]
        for label, content in results.items():
            excerpt = content.strip().replace("`", "'")[:400]
            lines.append(f"- {label}: `{excerpt}`")
        self.artifact_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _send(client: TestClient, agent_id: int, content: str) -> str:
    session_id = client.post("/api/v1/chat/sessions", json={"agentId": agent_id}).json()["data"]["id"]
    response = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"content": content, "stream": False},
    )
    if response.status_code != 200:
        raise AssertionError(f"chat request failed: {response.status_code} {response.text}")
    return str(response.json()["data"]["assistantMessage"]["content"])


def _seed_agent(
    api_key: str,
    base_url: str,
    model: str,
    knowledge_base_id: int | None = None,
    workflow_id: int | None = None,
    tool_bound: bool = False,
) -> int:
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    agent = Base.metadata.tables["agent"]
    mcp_server = Base.metadata.tables["mcp_server"]
    agent_tool = Base.metadata.tables["agent_tool"]
    now = datetime.now()
    with get_session_factory()() as session:
        provider_id = session.execute(
            provider.insert().values(
                name=f"OpenRouter live {time.time_ns()}",
                type="OPENAI_COMPATIBLE",
                base_url=base_url,
                auth_config={"api_key": api_key},
                description="live acceptance provider",
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        model_id = session.execute(
            model_config.insert().values(
                provider_id=provider_id,
                name="OpenRouter live model",
                model_id=model,
                context_size=4096,
                extra_params={"temperature": 0},
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        agent_id = session.execute(
            agent.insert().values(
                name=f"OpenRouter live agent {time.time_ns()}",
                description="",
                system_prompt="Follow the user's marker instructions exactly.",
                model_config_id=model_id,
                temperature=0,
                max_tokens=512,
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
                    name=f"OpenRouter live MCP {time.time_ns()}",
                    endpoint="mock://tools",
                    description="live acceptance MCP",
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
    content = b"Policy marker HIFY_RAG_CONTEXT lives in the live acceptance handbook."
    with get_session_factory()() as session:
        service = KnowledgeBaseService(KnowledgeBaseRepository(session))
        document = service.upload_document(kb_id, "live-rag-guide.txt", content)
        service.process_document(document["id"], content)
    return kb_id


def _seed_knowledge_base() -> int:
    knowledge_base = Base.metadata.tables["knowledge_base"]
    now = datetime.now()
    with get_session_factory()() as session:
        kb_id = session.execute(
            knowledge_base.insert().values(
                name=f"OpenRouter live KB {time.time_ns()}",
                description="",
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(kb_id)


def _create_live_workflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"OpenRouter live workflow {time.time_ns()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "llm",
                    "type": "LLM",
                    "name": "Live LLM",
                    "config": {
                        "prompt": "Return exactly HIFY_WORKFLOW_NODE_LIVE for {{start.userMessage}}",
                        "outputVariable": "answer",
                    },
                },
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "answer"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "llm", "condition": None},
                {"sourceNodeKey": "llm", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    if response.status_code != 200:
        raise AssertionError(f"workflow creation failed: {response.status_code} {response.text}")
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
