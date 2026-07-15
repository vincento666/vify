import time
import unittest
from datetime import datetime
from typing import Any
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory
from app.core.db_write import insert_and_get_id
from app.main import app
from app.modules.chat.domain.llm_request import FakeOpenAIChatClient


def _assistant_payload(content: str) -> dict[str, Any]:
    return {
        "model": "runtime-v2-test-response-model",
        "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
    }


class RuntimeV2ProviderBackedLlmBindingTest(unittest.TestCase):
    def setUp(self) -> None:
        _cleanup_seeded_live_agents()

    def tearDown(self) -> None:
        _cleanup_seeded_live_agents()

    def test_workflow_runs_v2_persists_llm_debug_usage_and_model_parameters(self) -> None:
        _seed_live_agent(model_id="runtime-v2-agent-model")
        fake_client = FakeOpenAIChatClient(response_payload=_assistant_payload("RUNTIME_V2_PROVIDER_OK"))

        with patch("app.modules.workflow.domain.service.ProviderBackedOpenAIChatClient", lambda _config: fake_client):
            with TestClient(app) as client:
                workflow = _create_llm_workflow(client)
                published = client.post(f"/api/v1/workflows/{workflow['id']}/publish")
                self.assertEqual(published.status_code, 200, published.text)
                started = client.post(
                    f"/api/v1/workflows/{workflow['id']}/runs",
                    json={"input": {"userMessage": "runtime v2 provider"}},
                ).json()["data"]
                terminal = _wait_for_result(client, started["resultRef"], "SUCCEEDED")
                nodes = client.get(started["nodesRef"]).json()["data"]["list"]
                events = client.get(started["eventsRef"]).json()["data"]["list"]

        self.assertEqual(terminal["output"]["answer"], "RUNTIME_V2_PROVIDER_OK")
        self.assertEqual(
            terminal["usage"],
            {"inputTokens": 11, "outputTokens": 7, "totalTokens": 18, "estimated": False},
        )
        self.assertNotIn("LLM mock:", str(terminal["output"]))
        self.assertEqual(fake_client.captured_payload["model"], "runtime-v2-node-model")
        self.assertEqual(fake_client.captured_payload["temperature"], 0.23)
        self.assertEqual(fake_client.captured_payload["max_tokens"], 41)
        self.assertEqual(fake_client.captured_payload["top_p"], 0.82)
        self.assertEqual(fake_client.captured_payload["seed"], 132)
        self.assertEqual(fake_client.captured_payload["response_format"], {"type": "json_object"})
        self.assertEqual(fake_client.captured_payload["stop"], ["END"])
        self.assertEqual(fake_client.captured_payload["messages"][-1]["content"], "Runtime v2 prompt: runtime v2 provider")

        llm_node = next(node for node in nodes if node["nodeKey"] == "llm")
        self.assertEqual(llm_node["outputs"]["answer"], "RUNTIME_V2_PROVIDER_OK")
        self.assertEqual(llm_node["outputs"]["__debug"]["llm"]["model"], "runtime-v2-test-response-model")
        self.assertEqual(llm_node["outputs"]["__usage"], {"inputTokens": 11, "outputTokens": 7, "totalTokens": 18, "estimated": False})
        completed = next(
            event
            for event in events
            if event["type"] == "workflow_node_completed" and event["nodeId"] == "llm"
        )
        self.assertEqual(completed["payload"]["output"]["__usage"]["totalTokens"], 18)

    def test_chatflow_runs_v2_records_provider_fallback_attempts_in_node_outputs(self) -> None:
        _seed_live_agent(model_id="runtime-v2-primary-model", extra_params={"fallbackModel": "runtime-v2-fallback-model"})
        fake_client = _FallbackOpenAIChatClient()

        with patch("app.modules.workflow.domain.service.ProviderBackedOpenAIChatClient", lambda _config: fake_client):
            with TestClient(app) as client:
                chatflow = _create_llm_chatflow(client)
                started = client.post(
                    f"/api/v1/chatflows/{chatflow['id']}/runs",
                    json={
                        "input": {
                            "sys.query": "need fallback",
                            "sys.conversation_id": f"runtime-v2-provider-{time.time_ns()}",
                            "sys.user_id": "runtime-v2-user",
                            "sys.channel": "web",
                        }
                    },
                ).json()["data"]
                terminal = _wait_for_result(client, started["resultRef"], "SUCCEEDED")
                nodes = client.get(started["nodesRef"]).json()["data"]["list"]

        self.assertEqual(terminal["output"]["answer"], "RUNTIME_V2_FALLBACK_OK")
        self.assertEqual([payload["model"] for payload in fake_client.captured_payloads], [
            "runtime-v2-primary-model",
            "runtime-v2-fallback-model",
        ])
        llm_node = next(node for node in nodes if node["nodeKey"] == "llm")
        debug = llm_node["outputs"]["__debug"]["llm"]
        self.assertTrue(debug["fallbackUsed"])
        self.assertEqual(debug["requestModel"], "runtime-v2-primary-model")
        self.assertEqual(debug["fallbackModel"], "runtime-v2-fallback-model")
        self.assertEqual(debug["fallback"]["attempts"][-1], {"model": "runtime-v2-fallback-model", "status": "succeeded"})
        self.assertNotIn("sk-runtime-v2-provider-test", str(llm_node["outputs"]))

    def test_chatflow_runs_v2_uses_node_model_config_without_live_agent(self) -> None:
        model_config_id = _seed_live_model_config(model_id="runtime-v2-direct-node-model")
        fake_client = FakeOpenAIChatClient(response_payload=_assistant_payload("RUNTIME_V2_DIRECT_MODEL_OK"))

        with patch("app.modules.workflow.domain.service.ProviderBackedOpenAIChatClient", lambda _config: fake_client):
            with TestClient(app) as client:
                chatflow = _create_llm_chatflow(client, llm_config={"modelConfigId": model_config_id})
                started = client.post(
                    f"/api/v1/chatflows/{chatflow['id']}/runs",
                    json={
                        "input": {
                            "sys.query": "direct node model",
                            "sys.conversation_id": f"runtime-v2-direct-{time.time_ns()}",
                            "sys.user_id": "runtime-v2-user",
                            "sys.channel": "web",
                        }
                    },
                ).json()["data"]
                terminal = _wait_for_result(client, started["resultRef"], "SUCCEEDED")
                nodes = client.get(started["nodesRef"]).json()["data"]["list"]

        self.assertEqual(terminal["output"]["answer"], "RUNTIME_V2_DIRECT_MODEL_OK")
        self.assertNotIn("LLM mock:", str(terminal["output"]))
        self.assertEqual(fake_client.captured_payload["model"], "runtime-v2-direct-node-model")
        llm_node = next(node for node in nodes if node["nodeKey"] == "llm")
        self.assertEqual(llm_node["outputs"]["__debug"]["llm"]["model"], "runtime-v2-test-response-model")
        self.assertEqual(llm_node["outputs"]["__usage"]["totalTokens"], 18)

    def test_chatflow_runs_v2_prefers_node_model_config_over_default_live_agent(self) -> None:
        model_config_id = _seed_live_model_config(model_id="runtime-v2-direct-node-model")
        _seed_live_agent(model_id="runtime-v2-contaminating-agent-model", cleanup=False)
        fake_client = FakeOpenAIChatClient(response_payload=_assistant_payload("RUNTIME_V2_DIRECT_MODEL_OK"))

        with patch("app.modules.workflow.domain.service.ProviderBackedOpenAIChatClient", lambda _config: fake_client):
            with TestClient(app) as client:
                chatflow = _create_llm_chatflow(client, llm_config={"modelConfigId": model_config_id})
                started = client.post(
                    f"/api/v1/chatflows/{chatflow['id']}/runs",
                    json={
                        "input": {
                            "sys.query": "direct node model",
                            "sys.conversation_id": f"runtime-v2-direct-priority-{time.time_ns()}",
                            "sys.user_id": "runtime-v2-user",
                            "sys.channel": "web",
                        }
                    },
                ).json()["data"]
                terminal = _wait_for_result(client, started["resultRef"], "SUCCEEDED")

        self.assertEqual(terminal["output"]["answer"], "RUNTIME_V2_DIRECT_MODEL_OK")
        self.assertEqual(fake_client.captured_payload["model"], "runtime-v2-direct-node-model")

    def test_chatflow_runs_v2_uses_node_model_config_for_llm_intent(self) -> None:
        model_config_id = _seed_live_model_config(model_id="runtime-v2-intent-model")
        fake_client = FakeOpenAIChatClient(response_payload=_assistant_payload("refund"))

        with patch("app.modules.workflow.domain.service.ProviderBackedOpenAIChatClient", lambda _config: fake_client):
            with TestClient(app) as client:
                chatflow = _create_llm_intent_chatflow(client, model_config_id=model_config_id)
                started = client.post(
                    f"/api/v1/chatflows/{chatflow['id']}/runs",
                    json={
                        "input": {
                            "sys.query": "opaque intent marker",
                            "sys.conversation_id": f"runtime-v2-intent-{time.time_ns()}",
                            "sys.user_id": "runtime-v2-user",
                            "sys.channel": "web",
                        }
                    },
                ).json()["data"]
                terminal = _wait_for_result(client, started["resultRef"], "SUCCEEDED")
                nodes = client.get(started["nodesRef"]).json()["data"]["list"]

        self.assertEqual(terminal["output"]["final"], "LLM_INTENT_REFUND")
        self.assertEqual(fake_client.captured_payload["model"], "runtime-v2-intent-model")
        self.assertEqual(fake_client.captured_payload["max_tokens"], 16)
        intent_node = next(node for node in nodes if node["nodeKey"] == "intent")
        self.assertEqual(intent_node["outputs"]["intent"], "refund")
        self.assertEqual(intent_node["outputs"]["reason"], "matched by llm classifier")
        self.assertEqual(intent_node["outputs"]["__usage"]["totalTokens"], 18)


def _seed_live_agent(model_id: str, extra_params: dict[str, Any] | None = None, cleanup: bool = True) -> int:
    model_config_id = _seed_live_model_config(model_id, extra_params, cleanup=cleanup)
    now = datetime.now()
    agent = Base.metadata.tables["agent"]
    with get_session_factory()() as session:
        agent_id = insert_and_get_id(
            session,
            agent,
            {
                "name": f"Runtime V2 Agent {time.time_ns()}",
                "description": "",
                "system_prompt": "You are a runtime v2 test agent.",
                "model_config_id": model_config_id,
                "temperature": 0.13,
                "max_tokens": 96,
                "max_context_turns": 6,
                "opening_message": "",
                "suggested_questions": [],
                "workflow_id": None,
                "enabled": True,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        session.commit()
    return int(agent_id)


def _seed_live_model_config(model_id: str, extra_params: dict[str, Any] | None = None, cleanup: bool = True) -> int:
    if cleanup:
        _cleanup_seeded_live_agents()
    now = datetime.now()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    with get_session_factory()() as session:
        provider_id = insert_and_get_id(
            session,
            provider,
            {
                "name": f"Runtime V2 Provider {time.time_ns()}",
                "type": "OPENAI",
                "base_url": "https://runtime-v2-provider.example.test/v1",
                "auth_config": {"api_key": "sk-runtime-v2-provider-test"},
                "description": "",
                "enabled": True,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        model_config_id = insert_and_get_id(
            session,
            model_config,
            {
                "provider_id": provider_id,
                "name": model_id,
                "model_id": model_id,
                "context_size": 128000,
                "extra_params": dict(extra_params or {}),
                "enabled": True,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        session.commit()
    return int(model_config_id)


def _cleanup_seeded_live_agents() -> None:
    now = datetime.now()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    agent = Base.metadata.tables["agent"]
    with get_session_factory()() as session:
        session.execute(
            agent.update()
            .where(agent.c.name.like("Runtime V2 Agent %"))
            .values(deleted=True, enabled=False, updated_at=now)
        )
        session.execute(
            model_config.update()
            .where(model_config.c.model_id.like("runtime-v2-%"))
            .values(deleted=True, enabled=False, updated_at=now)
        )
        session.execute(
            provider.update()
            .where(provider.c.name.like("Runtime V2 Provider %"))
            .values(deleted=True, enabled=False, updated_at=now)
        )
        session.commit()


def _create_llm_workflow(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Runtime V2 Provider Workflow {time.time_ns()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "llm",
                    "type": "LLM",
                    "name": "Provider LLM",
                    "config": {
                        "prompt": "Runtime v2 prompt: {{start.userMessage}}",
                        "outputVariable": "answer",
                        "model": "runtime-v2-node-model",
                        "temperature": 0.23,
                        "maxTokens": 41,
                        "topP": 0.82,
                        "responseFormat": "JSON",
                        "stopSequences": "END",
                        "seed": 132,
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
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_llm_chatflow(client: TestClient, llm_config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = {"prompt": "Chatflow runtime v2 prompt: {{sys.query}}", "outputVariable": "answer"}
    config.update(llm_config or {})
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Runtime V2 Provider Chatflow {time.time_ns()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "llm",
                    "type": "LLM",
                    "name": "Provider LLM",
                    "config": config,
                },
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "answer"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "llm", "condition": None},
                {"sourceNodeKey": "llm", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_llm_intent_chatflow(client: TestClient, *, model_config_id: int) -> dict[str, Any]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Runtime V2 Provider Intent Chatflow {time.time_ns()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "intent",
                    "type": "INTENT_RECOGNITION",
                    "name": "Provider Intent",
                    "config": {
                        "inputSource": "{{start.sys.query}}",
                        "outputVariable": "intent",
                        "classifierMode": "llm",
                        "modelConfigId": model_config_id,
                        "maxTokens": 16,
                        "defaultIntent": "default",
                        "intents": [
                            {
                                "key": "refund",
                                "name": "Refund",
                                "description": "a refund request",
                                "examples": ["return"],
                            }
                        ],
                    },
                },
                {
                    "nodeKey": "refund_end",
                    "type": "END",
                    "name": "Refund",
                    "config": {"outputVariable": "final", "output": "LLM_INTENT_REFUND"},
                },
                {
                    "nodeKey": "default_end",
                    "type": "END",
                    "name": "Default",
                    "config": {"outputVariable": "final", "output": "FAKE_INTENT_DEFAULT"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "intent", "condition": None},
                {"sourceNodeKey": "intent", "targetNodeKey": "refund_end", "condition": "refund"},
                {"sourceNodeKey": "intent", "targetNodeKey": "default_end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _wait_for_result(client: TestClient, result_ref: str, wanted_status: str, timeout: float = 5.0) -> dict[str, Any]:
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


class _FallbackOpenAIChatClient(FakeOpenAIChatClient):
    def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.captured_payload = payload
        self.captured_payloads.append(payload)
        if payload.get("model") == "runtime-v2-primary-model":
            raise httpx.ConnectError("runtime-v2 primary unavailable")
        return _assistant_payload("RUNTIME_V2_FALLBACK_OK")


if __name__ == "__main__":
    unittest.main()
