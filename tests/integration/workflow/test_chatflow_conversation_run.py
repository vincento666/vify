import time
import unittest
from typing import Any

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.main import app
from app.modules.chat.domain.llm_request import FakeOpenAIChatClient
from app.modules.provider.api.schemas import ModelConfigDto
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.repository import WorkflowRepository
from app.modules.workflow.web.router import get_chatflow_service


def _assistant_payload(content: str) -> dict[str, Any]:
    return {
        "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"total_tokens": max(1, len(content.split()))},
    }


class ChatflowConversationRunTest(unittest.TestCase):
    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_chatflow_service, None)

    def test_chatflow_run_renders_system_variables(self) -> None:
        with TestClient(app) as client:
            create_response = client.post(
                "/api/v1/chatflows",
                json={
                    "name": f"Chatflow conversation {time.time_ns()}",
                    "description": "",
                    "nodes": [
                        {
                            "nodeKey": "start",
                            "type": "START",
                            "name": "Start",
                            "config": {"outputVariables": ["sys.query", "sys.channel"]},
                        },
                        {
                            "nodeKey": "end",
                            "type": "END",
                            "name": "End",
                            "config": {
                                "outputVariable": "output",
                                "output": "收到 {{sys.query}} via {{sys.channel}} for {{global.brand}}/{{global.locale}}",
                            },
                        },
                    ],
                    "edges": [{"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None}],
                },
            )
            chatflow = create_response.json()["data"]
            run_response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={
                    "input": {
                        "userMessage": "查订单",
                        "sys.query": "查订单",
                        "sys.channel": "web",
                        "global.brand": "Hify",
                        "global.locale": "zh-CN",
                    }
                },
            )

        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(run_response.status_code, 200)
        data = run_response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"]["output"], "收到 查订单 via web for Hify/zh-CN")
        self.assertEqual(
            data["streamEvents"],
            [
                {
                    "type": "message_delta",
                    "nodeKey": "end",
                    "content": "收到 查订单 via web for Hify/zh-CN",
                },
                {
                    "type": "message_done",
                    "nodeKey": "end",
                    "content": "收到 查订单 via web for Hify/zh-CN",
                },
            ],
        )

    def test_default_chatflow_run_does_not_500_when_end_output_is_empty(self) -> None:
        with TestClient(app) as client:
            create_response = client.post(
                "/api/v1/chatflows",
                json={
                    "name": f"Chatflow default run {time.time_ns()}",
                    "description": "",
                    "nodes": [
                        {
                            "nodeKey": "start",
                            "type": "START",
                            "name": "Start",
                            "config": {"outputVariables": ["sys.query", "sys.conversation_id", "sys.user_id", "sys.channel"]},
                        },
                        {
                            "nodeKey": "end",
                            "type": "END",
                            "name": "End",
                            "config": {"outputVariable": "output"},
                        },
                    ],
                    "edges": [{"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None}],
                },
            )
            chatflow = create_response.json()["data"]
            run_response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={
                    "input": {
                        "sys.query": "查订单",
                        "sys.conversation_id": "conv-default",
                        "sys.user_id": "user-default",
                        "sys.channel": "web",
                    }
                },
            )

        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(run_response.status_code, 200)
        data = run_response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"], {"output": None})
        self.assertEqual(data["streamEvents"], [])
        self.assertEqual(data["sessionId"], "conv-default")

    def test_chatflow_llm_run_emits_llm_delta_and_final_output(self) -> None:
        fake_client = FakeOpenAIChatClient(response_payload=_assistant_payload("CHATFLOW_LLM_STREAM_OK"))
        app.dependency_overrides[get_chatflow_service] = _service_override(fake_client)

        with TestClient(app) as client:
            create_response = client.post(
                "/api/v1/chatflows",
                json={
                    "name": f"Chatflow llm stream {time.time_ns()}",
                    "description": "",
                    "nodes": [
                        {"nodeKey": "start", "type": "START", "name": "Start", "config": {"outputVariables": ["sys.query"]}},
                        {
                            "nodeKey": "llm_1",
                            "type": "LLM",
                            "name": "LLM",
                            "config": {"prompt": "User: {{start.sys.query}}", "outputVariable": "answer"},
                        },
                        {
                            "nodeKey": "end",
                            "type": "END",
                            "name": "End",
                            "config": {"outputVariable": "final", "output": "Final {{llm_1.answer}}"},
                        },
                    ],
                    "edges": [
                        {"sourceNodeKey": "start", "targetNodeKey": "llm_1", "condition": None},
                        {"sourceNodeKey": "llm_1", "targetNodeKey": "end", "condition": None},
                    ],
                },
            )
            chatflow = create_response.json()["data"]
            run_response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={"input": {"sys.query": "refund"}},
            )

        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(run_response.status_code, 200)
        data = run_response.json()["data"]
        final = data["output"]["final"]
        self.assertEqual(final, "Final CHATFLOW_LLM_STREAM_OK")
        answer = "CHATFLOW_LLM_STREAM_OK"
        self.assertEqual(
            [(event["type"], event["nodeKey"], event["content"]) for event in data["streamEvents"]],
            [
                ("llm_delta", "llm_1", answer),
                ("message_done", "llm_1", answer),
                ("node_usage", "llm_1", ""),
                ("message_delta", "end", final),
                ("message_done", "end", final),
            ],
        )


def _service_override(fake_client: FakeOpenAIChatClient):
    def override(session: Session = Depends(get_session)) -> WorkflowService:
        return WorkflowService(
            WorkflowRepository(session),
            flow_type="CHATFLOW",
            agent_repository=_AgentRepositoryStub(),
            model_facade=_ModelFacadeStub(),
            chatflow_state_repository=ChatflowStateRepository(session),
            llm_client_factory=lambda _config: fake_client,
        )

    return override


class _AgentRepositoryStub:
    def find_default_live_llm_agent(self) -> dict[str, Any]:
        return {
            "id": 501,
            "name": "Chatflow Test Agent",
            "system_prompt": "You are the chatflow test agent.",
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
