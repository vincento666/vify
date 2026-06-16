import unittest
from datetime import datetime
from typing import Any

from fastapi import Depends
from fastapi.testclient import TestClient
import httpx
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.main import app
from app.modules.chat.domain.llm_request import FakeOpenAIChatClient
from app.modules.provider.api.schemas import ModelConfigDto
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.infra.repository import WorkflowRepository
from app.modules.workflow.web.router import get_chatflow_service, get_workflow_service


def _assistant_payload(content: str) -> dict[str, Any]:
    return {
        "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"total_tokens": max(1, len(content.split()))},
    }


class WorkflowNodeRunIntegrationTest(unittest.TestCase):
    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_workflow_service, None)
        app.dependency_overrides.pop(get_chatflow_service, None)

    def test_selected_llm_node_run_does_not_continue_downstream(self) -> None:
        fake_client = FakeOpenAIChatClient(response_payload=_assistant_payload("NODE_ONLY_RESPONSE"))
        app.dependency_overrides[get_workflow_service] = _service_override(fake_client)

        with TestClient(app) as client:
            workflow = _create_node_run_workflow(client)
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/nodes/llm/runs",
                json={"input": {"userMessage": "node fixture"}},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["nodeKey"], "llm")
        self.assertEqual(data["output"]["answer"], "NODE_ONLY_RESPONSE")
        self.assertEqual([event["type"] for event in data["output"]["events"]], ["llm_delta", "message_done", "node_usage"])
        self.assertGreater(data["output"]["__usage"]["totalTokens"], 0)
        self.assertEqual(data["input"], {"userMessage": "node fixture"})

    def test_selected_llm_node_run_exposes_fallback_debug(self) -> None:
        fake_client = _FallbackOpenAIChatClient()
        app.dependency_overrides[get_workflow_service] = _service_override(
            fake_client,
            model_extra_params={"fallbackModel": "xiaomi/mimo-v2-fallback"},
        )

        with TestClient(app) as client:
            workflow = _create_node_run_workflow(client)
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/nodes/llm/runs",
                json={"input": {"userMessage": "node fixture"}},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"]["answer"], "FALLBACK_NODE_RESPONSE")
        self.assertEqual([payload["model"] for payload in fake_client.captured_payloads], [
            "xiaomi/mimo-v2-flash",
            "xiaomi/mimo-v2-fallback",
        ])
        debug = data["output"]["__debug"]["llm"]
        self.assertEqual(debug["model"], "xiaomi/mimo-v2-fallback")
        self.assertEqual(debug["requestModel"], "xiaomi/mimo-v2-flash")
        self.assertEqual(debug["fallbackModel"], "xiaomi/mimo-v2-fallback")
        self.assertTrue(debug["fallbackUsed"])
        self.assertIn("模型服务网络不可达", debug["fallbackReason"])
        self.assertEqual(debug["fallback"]["attempts"][-1], {"model": "xiaomi/mimo-v2-fallback", "status": "succeeded"})

    def test_selected_node_run_rejects_missing_node(self) -> None:
        fake_client = FakeOpenAIChatClient(response_payload=_assistant_payload("NODE_ONLY_RESPONSE"))
        app.dependency_overrides[get_workflow_service] = _service_override(fake_client)

        with TestClient(app) as client:
            workflow = _create_node_run_workflow(client)
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/nodes/missing/runs",
                json={"input": {"userMessage": "node fixture"}},
            )

        self.assertEqual(response.status_code, 404)
        self.assertIn("Workflow node not found", response.json()["message"])

    def test_chatflow_selected_llm_node_uses_runtime_profile_without_downstream(self) -> None:
        fake_client = FakeOpenAIChatClient(response_payload=_assistant_payload("CHAT_NODE_ONLY_RESPONSE"))
        app.dependency_overrides[get_chatflow_service] = _service_override(fake_client, flow_type="CHATFLOW")

        with TestClient(app) as client:
            chatflow = _create_chatflow_node_run_workflow(client)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/nodes/llm/runs",
                json={
                    "input": {
                        "sys.query": "refund node fixture",
                        "sys.conversation_id": "conv-test",
                        "sys.user_id": "user-test",
                        "sys.channel": "web",
                        "history": [{"role": "user", "content": "previous refund message"}],
                    }
                },
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["nodeKey"], "llm")
        self.assertEqual(data["output"]["answer"], "CHAT_NODE_ONLY_RESPONSE")
        self.assertEqual([event["type"] for event in data["output"]["events"]], ["llm_delta", "message_done", "node_usage"])
        self.assertGreater(data["output"]["__usage"]["totalTokens"], 0)
        self.assertNotIn("DOWNSTREAM", str(data["output"]))
        captured_prompt = fake_client.captured_payload["messages"][-1]["content"]
        self.assertIn("Chatflow prompt: refund node fixture", captured_prompt)
        self.assertIn("Conversation History", captured_prompt)
        self.assertIn("previous refund message", captured_prompt)


def _service_override(
    fake_client: FakeOpenAIChatClient,
    flow_type: str = "WORKFLOW",
    model_extra_params: dict[str, Any] | None = None,
):
    def override(session: Session = Depends(get_session)) -> WorkflowService:
        return WorkflowService(
            WorkflowRepository(session),
            flow_type=flow_type,
            agent_repository=_AgentRepositoryStub(),
            model_facade=_ModelFacadeStub(extra_params=model_extra_params),
            llm_client_factory=lambda _config: fake_client,
        )

    return override


def _create_node_run_workflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Node Run Workflow {datetime.now().timestamp()}",
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
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "answer", "output": "DOWNSTREAM {{llm.answer}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "llm", "condition": None},
                {"sourceNodeKey": "llm", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    return response.json()["data"]


def _create_chatflow_node_run_workflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Node Run Chatflow {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {
                    "nodeKey": "start",
                    "type": "START",
                    "name": "Start",
                    "config": {"outputVariables": ["sys.query", "sys.conversation_id", "sys.user_id", "sys.channel"]},
                },
                {
                    "nodeKey": "llm",
                    "type": "LLM",
                    "name": "Answer",
                    "config": {
                        "prompt": "Chatflow prompt: {{sys.query}}",
                        "outputVariable": "answer",
                        "includeHistory": "true",
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "answer", "output": "DOWNSTREAM {{llm.answer}}"},
                },
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
    def __init__(self, extra_params: dict[str, Any] | None = None) -> None:
        self._extra_params = extra_params or {}

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
            extra_params=self._extra_params,
        )


class _FallbackOpenAIChatClient(FakeOpenAIChatClient):
    def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.captured_payload = payload
        self.captured_payloads.append(payload)
        if payload.get("model") == "xiaomi/mimo-v2-flash":
            raise httpx.ConnectError("[Errno 8] nodename nor servname provided, or not known")
        return {
            "model": str(payload.get("model") or ""),
            "choices": [{"message": {"role": "assistant", "content": "FALLBACK_NODE_RESPONSE"}, "finish_reason": "stop"}],
            "usage": {"total_tokens": 3},
        }


if __name__ == "__main__":
    unittest.main()
