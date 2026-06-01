import unittest
from datetime import datetime
from typing import Any

from app.core.errors import BizError
from app.modules.chat.domain.llm_request import FakeOpenAIChatClient
from app.modules.provider.api.schemas import ModelConfigDto
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.web.schemas import WorkflowRunRequest


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


class _WorkflowRepositoryStub:
    def __init__(self) -> None:
        now = datetime.now()
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
                "config": {"prompt": "Canvas prompt: {{start.userMessage}}", "outputVariable": "answer"},
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

    def create_node_run(self, _run_id: int, _node_key: str, _node_type: str) -> int:
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
