import unittest
from datetime import datetime
from typing import Any

from app.core.errors import BizError
from app.modules.chat.domain.llm_request import FakeOpenAIChatClient
from app.modules.knowledge.api.facade import KnowledgeSearchResult
from app.modules.provider.api.schemas import ModelConfigDto
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.web.schemas import WorkflowRunRequest


def _assistant_payload(content: str) -> dict[str, Any]:
    return {
        "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"total_tokens": max(1, len(content.split()))},
    }


class ChatflowResourceContextTest(unittest.TestCase):
    def test_chatflow_llm_resource_context_includes_sys_query_and_history(self) -> None:
        fake_client = FakeOpenAIChatClient(response_payload=_assistant_payload("CHATFLOW_RESOURCE_OK"))
        knowledge_facade = _KnowledgeFacadeStub()
        service = WorkflowService(
            _ChatflowRepositoryStub(),
            flow_type="CHATFLOW",
            agent_repository=_AgentRepositoryStub(),
            model_facade=_ModelFacadeStub(),
            knowledge_facade=knowledge_facade,
            llm_client_factory=lambda _config: fake_client,
        )

        result = service.execute(
            901,
            WorkflowRunRequest(input={
                "sys.query": "refund",
                "history": [{"role": "user", "content": "previous refund question"}],
            }),
        )

        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(result["output"]["answer"], "CHATFLOW_RESOURCE_OK")
        self.assertEqual(knowledge_facade.requests, [(42, "Lookup refund", 1)])
        model_prompt = fake_client.captured_payload["messages"][-1]["content"]
        self.assertIn("Knowledge Context", model_prompt)
        self.assertIn("Refunds are available within 7 days.", model_prompt)
        self.assertIn("Conversation History", model_prompt)
        self.assertIn("previous refund question", model_prompt)
        self.assertIn("Chatflow prompt: refund", model_prompt)

    def test_chatflow_llm_mcp_resource_requires_tool_runtime(self) -> None:
        service = WorkflowService(
            _ChatflowRepositoryStub(resources=[{"type": "MCP_TOOL", "id": 7}], include_history=False),
            flow_type="CHATFLOW",
            agent_repository=_AgentRepositoryStub(),
            model_facade=_ModelFacadeStub(),
            knowledge_facade=_KnowledgeFacadeStub(),
            llm_client_factory=lambda _config: FakeOpenAIChatClient(response_payload=_assistant_payload("NOPE")),
        )

        with self.assertRaises(BizError) as error:
            service.execute(901, WorkflowRunRequest(input={"sys.query": "weather"}))

        self.assertIn("LLM callable tools require a tool runtime", str(error.exception))


class _ChatflowRepositoryStub:
    def __init__(self, resources: list[dict[str, Any]] | None = None, include_history: bool = True) -> None:
        now = datetime.now()
        self.workflow = {
            "id": 901,
            "name": "Chatflow resource",
            "description": "",
            "flow_type": "CHATFLOW",
            "status": "DRAFT",
            "created_at": now,
            "updated_at": now,
        }
        self._resources = resources if resources is not None else [{
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseId": 42,
            "query": "Lookup {{sys.query}}",
            "topK": 1,
        }]
        self._include_history = include_history

    def get(self, workflow_id: int, _flow_type: str | None = None) -> dict[str, Any] | None:
        return self.workflow if workflow_id == 901 else None

    def list_nodes(self, _workflow_id: int) -> list[dict[str, Any]]:
        return [
            {"node_key": "start", "type": "START", "name": "Start", "config": {}},
            {
                "node_key": "llm",
                "type": "LLM",
                "name": "Answer",
                "config": {
                    "prompt": "Chatflow prompt: {{sys.query}}",
                    "outputVariable": "answer",
                    "resources": self._resources,
                    "includeHistory": "true" if self._include_history else "",
                },
            },
            {"node_key": "end", "type": "END", "name": "End", "config": {"outputVariable": "answer"}},
        ]

    def list_edges(self, _workflow_id: int) -> list[dict[str, Any]]:
        return [
            {"source_node_key": "start", "target_node_key": "llm", "condition_expr": None},
            {"source_node_key": "llm", "target_node_key": "end", "condition_expr": None},
        ]

    def create_run(self, _workflow_id: int, _input_data: dict[str, Any]) -> int:
        return 9901

    def create_node_run(
        self,
        _run_id: int,
        _node_key: str,
        _node_type: str,
        inputs: dict[str, object] | None = None,
    ) -> int:
        del inputs
        return 88

    def finish_node_run(
        self,
        _node_run_id: int,
        _status: str,
        outputs: dict[str, Any],
        error: str | None = None,
        elapsed_ms: int = 0,
    ) -> None:
        return None

    def finish_run(
        self,
        _run_id: int,
        _status: str,
        output: dict[str, Any],
        error: str | None = None,
    ) -> None:
        return None


class _AgentRepositoryStub:
    def find_default_live_llm_agent(self) -> dict[str, Any]:
        return {
            "id": 501,
            "name": "Canvas Live Agent",
            "system_prompt": "You are the chatflow canvas agent.",
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
            provider_auth_config={"api_key": "unit-test-key"},
            name="Mimo Flash",
            model_id="xiaomi/mimo-v2-flash",
            context_size=128000,
            extra_params={},
        )


class _KnowledgeFacadeStub:
    def __init__(self) -> None:
        self.requests: list[tuple[int, str, int]] = []

    def search_chunks(
        self,
        knowledge_base_id: int,
        query: str,
        top_k: int = 3,
        retrieval_mode: str | None = None,
        score_threshold: float | None = None,
        rerank: bool | None = None,
    ) -> list[KnowledgeSearchResult]:
        del retrieval_mode, score_threshold, rerank
        self.requests.append((knowledge_base_id, query, top_k))
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
