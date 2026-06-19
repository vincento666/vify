import json
import time
import unittest
from datetime import datetime
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.modules.chat.domain.llm_request import FakeOpenAIChatClient
from tests.integration.workflow.test_runtime_v2_provider_backed_llm import (
    _cleanup_seeded_live_agents,
    _seed_live_model_config,
)


class RuntimeV2LlmCallableToolsIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        _cleanup_seeded_live_agents()

    def tearDown(self) -> None:
        _cleanup_seeded_live_agents()

    def test_chatflow_runtime_v2_llm_node_invokes_callable_mcp_tool(self) -> None:
        model_config_id = _seed_live_model_config(model_id="runtime-v2-callable-tools-model")
        fake_client = FakeOpenAIChatClient(
            response_payloads=[
                _assistant_tool_call_payload("lookup_order", {"orderId": "A-194"}),
                _assistant_payload("Final answer: Order A-194 status: SHIPPED"),
            ],
        )

        with patch("app.modules.workflow.domain.service.ProviderBackedOpenAIChatClient", lambda _config: fake_client):
            with TestClient(app) as client:
                server_id = _create_mcp_server(client)
                chatflow = _create_llm_tool_chatflow(client, server_id, model_config_id)
                started_response = client.post(
                    f"/api/v1/chatflows/{chatflow['id']}/runs-v2",
                    json={"input": {"sys.query": "Where is order A-194?"}},
                )
                started = started_response.json()["data"]
                terminal = _wait_for_result(client, started["resultRef"])
                nodes = client.get(started["nodesRef"]).json()["data"]["list"]

        self.assertEqual(started_response.status_code, 200, started_response.text)
        self.assertEqual(terminal["status"], "SUCCEEDED")
        self.assertEqual(terminal["output"], {"final": "Final answer: Order A-194 status: SHIPPED"})
        llm_node = next(node for node in nodes if node["nodeKey"] == "llm_1")
        self.assertEqual(llm_node["outputs"]["answer"], "Final answer: Order A-194 status: SHIPPED")
        self.assertEqual(llm_node["outputs"]["toolCalls"][0]["toolName"], "lookup_order")
        self.assertTrue(llm_node["outputs"]["toolCalls"][0]["success"])
        self.assertIn("Order A-194 status: SHIPPED", llm_node["outputs"]["toolCalls"][0]["content"])
        self.assertEqual(fake_client.captured_payloads[0]["tools"][0]["function"]["name"], "lookup_order")
        self.assertEqual(fake_client.captured_payloads[0]["tool_choice"], "required")
        self.assertNotIn("tools", fake_client.captured_payloads[1])


def _assistant_payload(content: str) -> dict[str, Any]:
    return {
        "model": "runtime-v2-callable-response-model",
        "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 9, "completion_tokens": 7, "total_tokens": 16},
    }


def _assistant_tool_call_payload(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "model": "runtime-v2-callable-response-model",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_runtime_v2_lookup",
                            "type": "function",
                            "function": {"name": tool_name, "arguments": json.dumps(arguments)},
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 8, "completion_tokens": 3, "total_tokens": 11},
    }


def _wait_for_result(client: TestClient, result_ref: str, wanted_status: str = "SUCCEEDED", timeout: float = 5.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    latest: dict[str, Any] = {}
    while time.monotonic() < deadline:
        latest = client.get(result_ref).json()["data"]
        if latest["status"] == wanted_status:
            return latest
        if latest["status"] in {"FAILED", "CANCELLED", "INTERRUPTED"} and latest["status"] != wanted_status:
            raise AssertionError(f"Expected {wanted_status}, got {latest}")
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for {wanted_status}; latest={latest}")


def _create_mcp_server(client: TestClient) -> int:
    response = client.post(
        "/api/v1/mcp-servers",
        json={
            "name": f"Runtime V2 LLM Callable MCP {datetime.now().timestamp()}",
            "endpoint": "mock://tools",
            "description": "runtime v2 llm callable fixture",
            "enabled": True,
        },
    )
    assert response.status_code == 200, response.text
    return int(response.json()["data"]["id"])


def _create_llm_tool_chatflow(client: TestClient, server_id: int, model_config_id: int) -> dict[str, Any]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Runtime V2 LLM Callable Chatflow {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "llm_1",
                    "type": "LLM",
                    "name": "LLM With Tool",
                    "config": {
                        "prompt": "{{start.sys.query}}",
                        "outputVariable": "answer",
                        "modelConfigId": model_config_id,
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
                            {"name": "__debug", "type": "object"},
                            {"name": "__usage", "type": "object"},
                        ],
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{llm_1.answer}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "llm_1", "condition": None},
                {"sourceNodeKey": "llm_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
