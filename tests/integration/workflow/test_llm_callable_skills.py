import json
import unittest
from datetime import datetime
from typing import Any

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.main import app
from app.modules.chat.domain.llm_request import FakeOpenAIChatClient
from app.modules.mcp.api.facade import McpFacade
from app.modules.provider.api.schemas import ModelConfigDto
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.infra.repository import WorkflowRepository
from app.modules.workflow.web.router import get_workflow_service


class WorkflowLlmCallableSkillsIntegrationTest(unittest.TestCase):
    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_workflow_service, None)

    def test_llm_node_runs_one_model_tool_model_round_with_selected_mcp_skill(self) -> None:
        fake_client = FakeOpenAIChatClient(
            response_payloads=[
                _assistant_tool_call_payload("lookup_order", {"orderId": "A-700"}),
                _assistant_payload("Final answer: Order A-700 status: SHIPPED"),
            ],
        )
        app.dependency_overrides[get_workflow_service] = _service_override(fake_client)

        with TestClient(app) as client:
            server_id = _create_mcp_server(client)
            workflow = _create_llm_tool_workflow(client, server_id)
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/nodes/llm_1/runs",
                json={"input": {"orderId": "A-700"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"]["answer"], "Final answer: Order A-700 status: SHIPPED")
        self.assertEqual(data["output"]["toolCalls"][0]["toolName"], "lookup_order")
        self.assertTrue(data["output"]["toolCalls"][0]["success"])
        self.assertIn("Order A-700 status: SHIPPED", data["output"]["toolCalls"][0]["content"])
        self.assertEqual(len(fake_client.captured_payloads), 2)
        self.assertEqual(fake_client.captured_payloads[0]["tools"][0]["function"]["name"], "lookup_order")
        self.assertEqual(fake_client.captured_payloads[0]["tool_choice"], "required")
        self.assertNotIn("tools", fake_client.captured_payloads[1])

    def test_llm_callable_skills_reject_provider_without_tool_call_capability(self) -> None:
        fake_client = FakeOpenAIChatClient(response_payload=_assistant_payload("unused"))
        app.dependency_overrides[get_workflow_service] = _service_override(fake_client, provider_type="ANTHROPIC")

        with TestClient(app) as client:
            server_id = _create_mcp_server(client)
            workflow = _create_llm_tool_workflow(client, server_id)
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/nodes/llm_1/runs",
                json={"input": {"orderId": "A-701"}},
            )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("does not support tool calls", response.json()["message"])


def _assistant_payload(content: str) -> dict[str, Any]:
    return {
        "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"total_tokens": max(1, len(content.split()))},
    }


def _assistant_tool_call_payload(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_workflow_lookup",
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": json.dumps(arguments),
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"total_tokens": 3},
    }


def _service_override(fake_client: FakeOpenAIChatClient, provider_type: str = "OPENAI"):
    def override(session: Session = Depends(get_session)) -> WorkflowService:
        return WorkflowService(
            WorkflowRepository(session),
            flow_type="WORKFLOW",
            agent_repository=_AgentRepositoryStub(),
            model_facade=_ModelFacadeStub(provider_type),
            llm_client_factory=lambda _config: fake_client,
            mcp_tool_executor=McpFacade(session),
        )

    return override


def _create_mcp_server(client: TestClient) -> int:
    response = client.post(
        "/api/v1/mcp-servers",
        json={
            "name": f"LLM Callable MCP {datetime.now().timestamp()}",
            "endpoint": "mock://tools",
            "description": "llm callable skill fixture",
            "enabled": True,
        },
    )
    assert response.status_code == 200, response.text
    return int(response.json()["data"]["id"])


def _create_llm_tool_workflow(client: TestClient, server_id: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"LLM Callable Tool Workflow {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "llm_1",
                    "type": "LLM",
                    "name": "LLM With Tool",
                    "config": {
                        "prompt": "Where is order {{start.orderId}}?",
                        "outputVariable": "answer",
                        "toolChoiceMode": "required",
                        "maxToolRounds": 1,
                        "resources": [
                            {
                                "type": "MCP_TOOL",
                                "resourceType": "MCP_TOOL",
                                "resourceId": f"mcp:{server_id}:lookup_order",
                                "serverIds": [server_id],
                                "toolName": "lookup_order",
                                "enabled": True,
                            }
                        ],
                        "outputParameters": [
                            {"name": "answer", "type": "string"},
                            {"name": "toolCalls", "type": "array"},
                        ],
                    },
                },
            ],
            "edges": [{"sourceNodeKey": "start", "targetNodeKey": "llm_1", "condition": None}],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


class _AgentRepositoryStub:
    def find_default_live_llm_agent(self) -> dict[str, Any]:
        return {
            "id": 501,
            "name": "Workflow Tool Agent",
            "system_prompt": "Use tools when useful.",
            "model_config_id": 601,
            "temperature": 0.1,
            "max_tokens": 128,
            "enabled": True,
        }


class _ModelFacadeStub:
    def __init__(self, provider_type: str) -> None:
        self._provider_type = provider_type

    def get_enabled_model_config(self, model_config_id: int) -> ModelConfigDto:
        return ModelConfigDto(
            id=model_config_id,
            provider_id=701,
            provider_type=self._provider_type,
            provider_base_url="https://openrouter.ai/api/v1",
            provider_auth_config={"api_key": "integration-test-key"},
            name="Workflow Tool Model",
            model_id="workflow-tool-model",
            context_size=128000,
            extra_params={},
        )


if __name__ == "__main__":
    unittest.main()
