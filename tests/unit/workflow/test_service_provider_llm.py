import unittest
from datetime import datetime
from typing import Any

from app.core.errors import BizError
from app.modules.chat.domain.llm_request import FakeOpenAIChatClient
from app.modules.knowledge.api.facade import KnowledgeSearchResult
from app.modules.provider.api.schemas import ModelConfigDto
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.web.schemas import WorkflowNodeRunRequest, WorkflowRunRequest


def _assistant_payload(content: str) -> dict[str, Any]:
    return {
        "choices": [
            {
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"total_tokens": max(1, len(content.split()))},
    }


class WorkflowServiceProviderLlmTest(unittest.TestCase):
    def test_execute_uses_default_live_agent_for_llm_node(self) -> None:
        repository = _WorkflowRepositoryStub()
        fake_client = FakeOpenAIChatClient(response_payload=_assistant_payload("LIVE_WORKFLOW_AGENT_RESPONSE"))
        service = WorkflowService(
            repository,
            flow_type="WORKFLOW",
            agent_repository=_AgentRepositoryStub(),
            model_facade=_ModelFacadeStub(),
            llm_client_factory=lambda _config: fake_client,
        )

        result = service.execute(123, WorkflowRunRequest(input={"userMessage": "canvas live path"}))

        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(result["output"]["answer"], "LIVE_WORKFLOW_AGENT_RESPONSE")
        self.assertNotIn("LLM mock:", result["output"]["answer"])
        self.assertEqual(fake_client.captured_payload["model"], "xiaomi/mimo-v2-flash")
        self.assertEqual(fake_client.captured_payload["messages"][-1]["content"], "Canvas prompt: canvas live path")

    def test_execute_rejects_llm_node_when_no_live_agent_exists(self) -> None:
        service = WorkflowService(
            _WorkflowRepositoryStub(),
            flow_type="WORKFLOW",
            agent_repository=_EmptyAgentRepositoryStub(),
            model_facade=_ModelFacadeStub(),
        )

        with self.assertRaises(BizError) as error:
            service.execute(123, WorkflowRunRequest(input={"userMessage": "canvas live path"}))

        self.assertIn("Workflow LLM agent is not configured", str(error.exception))

    def test_execute_retries_with_model_config_fallback_model(self) -> None:
        repository = _WorkflowRepositoryStub()
        fake_client = _FailOnceOpenAIChatClient("FALLBACK_RESPONSE")
        service = WorkflowService(
            repository,
            flow_type="WORKFLOW",
            agent_repository=_AgentRepositoryStub(),
            model_facade=_FallbackModelFacadeStub(),
            llm_client_factory=lambda _config: fake_client,
        )

        result = service.execute(123, WorkflowRunRequest(input={"userMessage": "canvas live path"}))

        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(result["output"]["answer"], "FALLBACK_RESPONSE")
        self.assertEqual([payload["model"] for payload in fake_client.captured_payloads], ["qwen/qwen3.5-9b", "deepseek/deepseek-v4-flash"])

    def test_execute_can_prefer_named_live_agent_for_llm_node(self) -> None:
        repository = _WorkflowRepositoryStub()
        agent_repository = _PreferredAgentRepositoryStub()
        fake_client = FakeOpenAIChatClient(response_payload=_assistant_payload("PREFERRED_AGENT_RESPONSE"))
        service = WorkflowService(
            repository,
            flow_type="CHATFLOW",
            agent_repository=agent_repository,
            model_facade=_PreferredModelFacadeStub(),
            llm_client_factory=lambda _config: fake_client,
            preferred_llm_agent_name="034 RuntimeLab Airline Chatflow LLM Agent",
        )

        result = service.execute(123, WorkflowRunRequest(input={"sys.query": "runtime lab"}))

        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(result["output"]["answer"], "PREFERRED_AGENT_RESPONSE")
        self.assertEqual(agent_repository.requested_names, ["034 RuntimeLab Airline Chatflow LLM Agent"])
        self.assertEqual(fake_client.captured_payload["model"], "qwen/qwen3.5-9b")

    def test_execute_appends_knowledge_resource_context_before_llm_call(self) -> None:
        repository = _WorkflowRepositoryStub(
            llm_config={
                "prompt": "Canvas prompt: {{start.userMessage}}",
                "outputVariable": "answer",
                "resources": [
                    {
                        "type": "KNOWLEDGE_BASE",
                        "knowledgeBaseId": 42,
                        "query": "Lookup {{start.userMessage}}",
                        "topK": 2,
                    }
                ],
            }
        )
        knowledge_facade = _KnowledgeFacadeStub()
        fake_client = FakeOpenAIChatClient(response_payload=_assistant_payload("RESOURCE_CONTEXT_OK"))
        service = WorkflowService(
            repository,
            flow_type="WORKFLOW",
            agent_repository=_AgentRepositoryStub(),
            model_facade=_ModelFacadeStub(),
            knowledge_facade=knowledge_facade,
            llm_client_factory=lambda _config: fake_client,
        )

        result = service.execute(123, WorkflowRunRequest(input={"userMessage": "refund"}))

        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(result["output"]["answer"], "RESOURCE_CONTEXT_OK")
        self.assertEqual(knowledge_facade.requests, [(42, "Lookup refund", 2)])
        model_visible_prompt = fake_client.captured_payload["messages"][-1]["content"]
        self.assertIn("Canvas prompt: refund", model_visible_prompt)
        self.assertIn("Knowledge Context", model_visible_prompt)
        self.assertIn("Refunds are available within 7 days.", model_visible_prompt)

    def test_execute_rejects_llm_mcp_resource_without_tool_runtime(self) -> None:
        repository = _WorkflowRepositoryStub(
            llm_config={
                "prompt": "Canvas prompt: {{start.userMessage}}",
                "outputVariable": "answer",
                "resources": [{"type": "MCP_TOOL", "id": 7, "name": "weather"}],
            }
        )
        fake_client = FakeOpenAIChatClient(response_payload=_assistant_payload("SHOULD_NOT_RUN"))
        service = WorkflowService(
            repository,
            flow_type="WORKFLOW",
            agent_repository=_AgentRepositoryStub(),
            model_facade=_ModelFacadeStub(),
            knowledge_facade=_KnowledgeFacadeStub(),
            llm_client_factory=lambda _config: fake_client,
        )

        with self.assertRaises(BizError) as error:
            service.execute(123, WorkflowRunRequest(input={"userMessage": "canvas live path"}))

        self.assertIn("LLM callable tools require a tool runtime", str(error.exception))

    def test_run_node_executes_only_selected_llm_node_with_fixture_context(self) -> None:
        repository = _WorkflowRepositoryStub()
        fake_client = FakeOpenAIChatClient(response_payload=_assistant_payload("NODE_ONLY_RESPONSE"))
        service = WorkflowService(
            repository,
            flow_type="WORKFLOW",
            agent_repository=_AgentRepositoryStub(),
            model_facade=_ModelFacadeStub(),
            llm_client_factory=lambda _config: fake_client,
        )

        result = service.run_node(123, "llm", WorkflowNodeRunRequest(input={"userMessage": "node fixture"}))

        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(result["nodeKey"], "llm")
        self.assertEqual(result["output"]["answer"], "NODE_ONLY_RESPONSE")
        self.assertEqual([event["type"] for event in result["output"]["events"]], ["llm_delta", "message_done", "node_usage"])
        self.assertGreater(result["output"]["__usage"]["totalTokens"], 0)
        self.assertEqual(result["input"], {"userMessage": "node fixture"})
        self.assertEqual(fake_client.captured_payload["messages"][-1]["content"], "Canvas prompt: node fixture")

    def test_run_node_rejects_missing_node(self) -> None:
        service = WorkflowService(
            _WorkflowRepositoryStub(),
            flow_type="WORKFLOW",
            agent_repository=_AgentRepositoryStub(),
            model_facade=_ModelFacadeStub(),
        )

        with self.assertRaises(BizError) as error:
            service.run_node(123, "missing", WorkflowNodeRunRequest(input={"userMessage": "node fixture"}))

        self.assertIn("Workflow node not found", str(error.exception))


class _WorkflowRepositoryStub:
    def __init__(self, llm_config: dict[str, Any] | None = None) -> None:
        now = datetime.now()
        self._llm_config = llm_config or {
            "prompt": "Canvas prompt: {{start.userMessage}}",
            "outputVariable": "answer",
        }
        self.workflow = {
            "id": 123,
            "name": "Provider workflow",
            "description": "",
            "flow_type": "WORKFLOW",
            "status": "DRAFT",
            "created_at": now,
            "updated_at": now,
        }

    def get(self, workflow_id: int, _flow_type: str | None = None) -> dict[str, Any] | None:
        return self.workflow if workflow_id == 123 else None

    def list_nodes(self, _workflow_id: int) -> list[dict[str, Any]]:
        return [
            {"node_key": "start", "type": "START", "name": "Start", "config": {}},
            {
                "node_key": "llm",
                "type": "LLM",
                "name": "Answer",
                "config": self._llm_config,
            },
            {"node_key": "end", "type": "END", "name": "End", "config": {"outputVariable": "answer"}},
        ]

    def list_edges(self, _workflow_id: int) -> list[dict[str, Any]]:
        return [
            {"source_node_key": "start", "target_node_key": "llm", "condition_expr": None},
            {"source_node_key": "llm", "target_node_key": "end", "condition_expr": None},
        ]

    def create_run(self, _workflow_id: int, _input_data: dict[str, Any]) -> int:
        return 9001

    def create_node_run(
        self,
        _run_id: int,
        _node_key: str,
        _node_type: str,
        inputs: dict[str, object] | None = None,
    ) -> int:
        del inputs
        return 77

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
            "system_prompt": "You are the workflow canvas agent.",
            "model_config_id": 601,
            "temperature": 0.1,
            "max_tokens": 128,
            "enabled": True,
        }


class _PreferredAgentRepositoryStub(_AgentRepositoryStub):
    def __init__(self) -> None:
        self.requested_names: list[str] = []

    def find_live_llm_agent_by_name(self, name: str) -> dict[str, Any] | None:
        self.requested_names.append(name)
        return {
            "id": 502,
            "name": name,
            "system_prompt": "You are the runtime lab airline agent.",
            "model_config_id": 602,
            "temperature": 0,
            "max_tokens": 128,
            "enabled": True,
        }


class _EmptyAgentRepositoryStub:
    def find_default_live_llm_agent(self) -> None:
        return None


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


class _PreferredModelFacadeStub:
    def get_enabled_model_config(self, model_config_id: int) -> ModelConfigDto:
        return ModelConfigDto(
            id=model_config_id,
            provider_id=702,
            provider_type="OPENAI_COMPATIBLE",
            provider_base_url="https://openrouter.ai/api/v1",
            provider_auth_config={"api_key": "unit-test-key"},
            name="Runtime Lab qwen",
            model_id="qwen/qwen3.5-9b",
            context_size=8192,
            extra_params={"reasoning": {"effort": "none", "exclude": True}},
        )


class _FallbackModelFacadeStub:
    def get_enabled_model_config(self, model_config_id: int) -> ModelConfigDto:
        return ModelConfigDto(
            id=model_config_id,
            provider_id=701,
            provider_type="OPENAI_COMPATIBLE",
            provider_base_url="https://openrouter.ai/api/v1",
            provider_auth_config={"api_key": "unit-test-key"},
            name="Runtime Lab qwen",
            model_id="qwen/qwen3.5-9b",
            context_size=8192,
            extra_params={"fallbackModel": "deepseek/deepseek-v4-flash"},
        )


class _FailOnceOpenAIChatClient:
    def __init__(self, fallback_content: str) -> None:
        self.captured_payloads: list[dict[str, Any]] = []
        self._fallback_content = fallback_content

    def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.captured_payloads.append(payload)
        if len(self.captured_payloads) == 1:
            raise RuntimeError("primary model rate limited")
        return _assistant_payload(self._fallback_content)


class _KnowledgeFacadeStub:
    def __init__(self) -> None:
        self.requests: list[tuple[int, str, int]] = []

    def search_chunks(
        self,
        knowledge_base_id: int,
        query: str,
        top_k: int = 3,
        **_: Any,
    ) -> list[KnowledgeSearchResult]:
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
