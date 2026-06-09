import unittest
from datetime import datetime
from typing import Any

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.main import app
from app.modules.chat.domain.llm_request import FakeOpenAIChatClient
from app.modules.knowledge.api.facade import KnowledgeSearchResult
from app.modules.provider.api.schemas import ModelConfigDto
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.infra.repository import WorkflowRepository
from app.modules.workflow.web.router import get_workflow_service


def _assistant_payload(content: str) -> dict[str, Any]:
    return {
        "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"total_tokens": max(1, len(content.split()))},
    }


class WorkflowLlmResourceIntegrationTest(unittest.TestCase):
    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_workflow_service, None)

    def test_llm_knowledge_resource_context_reaches_model_prompt(self) -> None:
        fake_client = FakeOpenAIChatClient(response_payload=_assistant_payload("RESOURCE_CONTEXT_OK"))
        knowledge_facade = _KnowledgeFacadeStub()
        app.dependency_overrides[get_workflow_service] = _service_override(fake_client, knowledge_facade)

        with TestClient(app) as client:
            workflow = _create_llm_resource_workflow(client, resources=[{
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseId": 42,
                "query": "Lookup {{start.userMessage}}",
                "topK": 2,
                "retrievalMode": "faq",
                "scoreThreshold": 0.4,
                "rerank": True,
            }])
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"userMessage": "refund"}},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["output"]["answer"], "RESOURCE_CONTEXT_OK")
        self.assertEqual(
            knowledge_facade.requests,
            [
                {
                    "knowledge_base_id": 42,
                    "query": "Lookup refund",
                    "top_k": 2,
                    "retrieval_mode": "faq",
                    "score_threshold": 0.4,
                    "rerank": True,
                }
            ],
        )
        model_visible_prompt = fake_client.captured_payload["messages"][-1]["content"]
        self.assertIn("Canvas prompt: refund", model_visible_prompt)
        self.assertIn("Refunds are available within 7 days.", model_visible_prompt)

    def test_llm_mcp_resource_returns_bad_request_without_tool_runtime(self) -> None:
        fake_client = FakeOpenAIChatClient(response_payload=_assistant_payload("SHOULD_NOT_RUN"))
        app.dependency_overrides[get_workflow_service] = _service_override(fake_client, _KnowledgeFacadeStub())

        with TestClient(app) as client:
            workflow = _create_llm_resource_workflow(client, resources=[{
                "type": "MCP_TOOL",
                "id": 7,
                "name": "weather",
            }])
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"userMessage": "weather"}},
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("LLM callable tools require a tool runtime", response.json()["message"])


def _service_override(fake_client: FakeOpenAIChatClient, knowledge_facade: "_KnowledgeFacadeStub"):
    def override(session: Session = Depends(get_session)) -> WorkflowService:
        return WorkflowService(
            WorkflowRepository(session),
            flow_type="WORKFLOW",
            agent_repository=_AgentRepositoryStub(),
            model_facade=_ModelFacadeStub(),
            knowledge_facade=knowledge_facade,
            llm_client_factory=lambda _config: fake_client,
        )

    return override


def _create_llm_resource_workflow(client: TestClient, resources: list[dict[str, Any]]) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"LLM Resource Workflow {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "llm",
                    "type": "LLM",
                    "name": "Answer",
                    "config": {
                        "prompt": "Canvas prompt: {{start.userMessage}}",
                        "outputVariable": "answer",
                        "resources": resources,
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
    return response.json()["data"]


class _AgentRepositoryStub:
    def find_default_live_llm_agent(self) -> dict[str, Any]:
        return {
            "id": 501,
            "name": "Canvas Live Agent",
            "system_prompt": "You are the workflow canvas agent.",
            "model_config_id": 601,
            "temperature": 0.1,
            "max_tokens": 128,
            "enabled": True,
        }


class _ModelFacadeStub:
    def get_enabled_model_config(self, model_config_id: int) -> ModelConfigDto:
        return ModelConfigDto(
            id=model_config_id,
            provider_id=701,
            provider_type="OPENAI",
            provider_base_url="https://openrouter.ai/api/v1",
            provider_auth_config={"api_key": "integration-test-key"},
            name="Mimo Flash",
            model_id="xiaomi/mimo-v2-flash",
            context_size=128000,
            extra_params={},
        )


class _KnowledgeFacadeStub:
    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []

    def search_chunks(
        self,
        knowledge_base_id: int,
        query: str,
        top_k: int = 3,
        retrieval_mode: str | None = None,
        score_threshold: float | None = None,
        rerank: bool | None = None,
    ) -> list[KnowledgeSearchResult]:
        self.requests.append(
            {
                "knowledge_base_id": knowledge_base_id,
                "query": query,
                "top_k": top_k,
                "retrieval_mode": retrieval_mode,
                "score_threshold": score_threshold,
                "rerank": rerank,
            }
        )
        return [
            KnowledgeSearchResult(
                chunk_id=1,
                document_id=2,
                chunk_index=0,
                content="Refunds are available within 7 days.",
                token_count=7,
                score=0.98,
            )
        ]


if __name__ == "__main__":
    unittest.main()
