import unittest
from datetime import datetime
from typing import Any

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.main import app
from app.modules.chat.domain.llm_request import FakeOpenAIChatClient
from app.modules.provider.api.schemas import ModelConfigDto
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.infra.repository import WorkflowRepository
from app.modules.workflow.web.router import get_workflow_service


def _assistant_payload(content: str) -> dict[str, Any]:
    return {
        "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"total_tokens": max(1, len(content.split()))},
    }


class WorkflowLlmModelParametersIntegrationTest(unittest.TestCase):
    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_workflow_service, None)

    def test_llm_node_model_parameters_override_default_agent_payload(self) -> None:
        fake_client = FakeOpenAIChatClient(response_payload=_assistant_payload("PARAMETER_OK"))
        app.dependency_overrides[get_workflow_service] = _service_override(fake_client)

        with TestClient(app) as client:
            workflow = _create_workflow(client)
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"USER_INPUT": "parameter test"}},
            )

        self.assertEqual(response.status_code, 200)
        payload = fake_client.captured_payload
        self.assertEqual(payload["model"], "xiaomi/mimo-v2-flash")
        self.assertEqual(payload["temperature"], 0.23)
        self.assertEqual(payload["max_tokens"], 321)
        self.assertEqual(payload["top_p"], 0.81)
        self.assertEqual(payload["frequency_penalty"], 0.12)
        self.assertEqual(payload["presence_penalty"], 0.34)
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(payload["stop"], ["STOP_HERE"])
        self.assertEqual(payload["seed"], 42)
        self.assertEqual(payload["messages"][1]["role"], "system")
        self.assertIn("Node system prompt", payload["messages"][1]["content"])


def _service_override(fake_client: FakeOpenAIChatClient):
    def override(session: Session = Depends(get_session)) -> WorkflowService:
        return WorkflowService(
            WorkflowRepository(session),
            flow_type="WORKFLOW",
            agent_repository=_AgentRepositoryStub(),
            model_facade=_ModelFacadeStub(),
            llm_client_factory=lambda _config: fake_client,
        )

    return override


def _create_workflow(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"LLM Parameter Workflow {datetime.now().timestamp()}",
            "description": "model parameter integration",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {"outputVariables": ["USER_INPUT"]}},
                {
                    "nodeKey": "llm",
                    "type": "LLM",
                    "name": "LLM",
                    "config": {
                        "systemPrompt": "Node system prompt",
                        "prompt": "Input: {{start.USER_INPUT}}",
                        "model": "xiaomi/mimo-v2-flash",
                        "temperature": 0.23,
                        "maxTokens": 321,
                        "topP": 0.81,
                        "frequencyPenalty": 0.12,
                        "presencePenalty": 0.34,
                        "responseFormat": "JSON",
                        "stopSequences": ["STOP_HERE"],
                        "seed": 42,
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
    return response.json()["data"]


class _AgentRepositoryStub:
    def find_default_live_llm_agent(self) -> dict[str, Any]:
        return {
            "id": 501,
            "name": "Canvas Live Agent",
            "system_prompt": "Agent system prompt",
            "model_config_id": 601,
            "temperature": 0.9,
            "max_tokens": 2048,
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
            extra_params={"provider_default": "kept"},
        )


if __name__ == "__main__":
    unittest.main()
