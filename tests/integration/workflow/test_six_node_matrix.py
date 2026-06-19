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
from tests.support.local_api import LocalApiServer


def _assistant_payload(content: str) -> dict[str, Any]:
    return {
        "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"total_tokens": max(1, len(content.split()))},
    }


class WorkflowSixNodeMatrixIntegrationTest(unittest.TestCase):
    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_workflow_service, None)

    def test_workflow_api_runs_existing_six_node_matrix(self) -> None:
        fake_client = FakeOpenAIChatClient(response_payload=_assistant_payload("LLM_MATRIX_OK"))
        knowledge_facade = _KnowledgeFacadeStub()
        app.dependency_overrides[get_workflow_service] = _service_override(fake_client, knowledge_facade)
        server = LocalApiServer()
        server.start()
        self.addCleanup(server.stop)

        with TestClient(app) as client:
            workflow = _create_workflow(client, server.url)
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-legacy",
                json={"input": {"USER_INPUT": "kb"}},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(
            data["output"],
            {"final": "Final API_REAL: POST /text/LLM_MATRIX_OK"},
        )
        self.assertEqual(knowledge_facade.requests[0][:3], (42, "Matrix lookup", 2))
        self.assertIn("retrieval_mode", knowledge_facade.requests[0][3])
        captured_prompt = fake_client.captured_payload["messages"][-1]["content"]
        self.assertIn("Matrix KB context", captured_prompt)


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


def _create_workflow(client: TestClient, api_base_url: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Six Node Matrix {datetime.now().timestamp()}",
            "description": "integration six-node matrix",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {"outputVariables": ["USER_INPUT"]}},
                {
                    "nodeKey": "router",
                    "type": "CONDITION",
                    "name": "Router",
                    "config": {"expression": "{{start.USER_INPUT}}", "outputVariable": "route"},
                },
                {
                    "nodeKey": "kb",
                    "type": "KNOWLEDGE",
                    "name": "Knowledge",
                    "config": {
                        "query": "Matrix lookup",
                        "knowledgeBaseId": 42,
                        "topK": 2,
                        "outputVariable": "answer",
                    },
                },
                {
                    "nodeKey": "llm",
                    "type": "LLM",
                    "name": "LLM",
                    "config": {
                        "prompt": "Use the KB context only: {{kb.answer}}",
                        "outputVariable": "answer",
                    },
                },
                {
                    "nodeKey": "api",
                    "type": "API_CALL",
                    "name": "API",
                    "config": {
                        "method": "POST",
                        "endpoint": f"{api_base_url}/text/{{{{llm.answer}}}}",
                        "outputVariable": "response",
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "Final {{api.response}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "router", "condition": None},
                {"sourceNodeKey": "router", "targetNodeKey": "kb", "condition": "kb"},
                {"sourceNodeKey": "kb", "targetNodeKey": "llm", "condition": None},
                {"sourceNodeKey": "llm", "targetNodeKey": "api", "condition": None},
                {"sourceNodeKey": "api", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    return response.json()["data"]


class _KnowledgeFacadeStub:
    def __init__(self) -> None:
        self.requests: list[tuple[int, str, int, dict[str, Any]]] = []

    def search_chunks(
        self,
        knowledge_base_id: int,
        query: str,
        top_k: int = 3,
        **kwargs: Any,
    ) -> list[KnowledgeSearchResult]:
        self.requests.append((knowledge_base_id, query, top_k, kwargs))
        return [
            KnowledgeSearchResult(
                chunk_id=1,
                document_id=2,
                chunk_index=0,
                content="Matrix KB context",
                token_count=3,
                score=0.98,
            )
        ]


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


if __name__ == "__main__":
    unittest.main()
