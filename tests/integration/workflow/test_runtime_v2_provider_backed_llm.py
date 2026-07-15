import asyncio
import time
import threading
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

    def test_chatflow_v2_persists_provider_delta_before_llm_node_completion(self) -> None:
        model_config_id = _seed_live_model_config(model_id="runtime-v2-streaming-model")
        fake_client = _BlockingStreamingOpenAIClient(
            response_payload=_assistant_payload("first second"),
            chunks=["first ", "second"],
        )

        with patch("app.modules.workflow.domain.service.ProviderBackedOpenAIChatClient", lambda _config: fake_client):
            with TestClient(app) as client:
                chatflow = _create_llm_chatflow(client, llm_config={"modelConfigId": model_config_id})
                started = client.post(
                    f"/api/v1/chatflows/{chatflow['id']}/runs",
                    json={"input": {"sys.query": "stream this"}},
                ).json()["data"]

                self.assertTrue(fake_client.first_delta_sent.wait(timeout=3), "provider delta was not forwarded live")
                live_events = client.get(started["eventsRef"]).json()["data"]["list"]
                live_result = client.get(started["resultRef"]).json()["data"]
                fake_client.release_completion.set()
                terminal = _wait_for_result(client, started["resultRef"], "SUCCEEDED")
                terminal_events = client.get(started["eventsRef"]).json()["data"]["list"]

        live_deltas = [event for event in live_events if event["type"] == "llm_delta"]
        self.assertEqual([event["payload"]["content"] for event in live_deltas], ["first "])
        self.assertEqual(live_deltas[0]["payload"]["streamSource"], "provider")
        self.assertFalse(
            any(event["type"] == "workflow_node_completed" and event["nodeId"] == "llm" for event in live_events)
        )
        self.assertEqual(live_result["status"], "RUNNING")
        all_deltas = [event for event in terminal_events if event["type"] == "llm_delta"]
        self.assertEqual([event["payload"]["content"] for event in all_deltas], ["first ", "second"])
        self.assertEqual(terminal["output"]["answer"], "first second")
        self.assertLess(
            max(event["sequence"] for event in all_deltas),
            next(
                event["sequence"]
                for event in terminal_events
                if event["type"] == "workflow_node_completed" and event["nodeId"] == "llm"
            ),
        )

    def test_chatflow_v2_consumes_async_provider_stream_before_node_completion(self) -> None:
        model_config_id = _seed_live_model_config(model_id="runtime-v2-async-streaming-model")
        fake_client = _AsyncBlockingStreamingOpenAIClient(
            response_payload=_assistant_payload("first second"),
            chunks=["first ", "second"],
        )

        with patch("app.modules.workflow.domain.service.ProviderBackedOpenAIChatClient", lambda _config: fake_client):
            with TestClient(app) as client:
                chatflow = _create_llm_chatflow(client, llm_config={"modelConfigId": model_config_id})
                started = client.post(
                    f"/api/v1/chatflows/{chatflow['id']}/runs",
                    json={"input": {"sys.query": "async stream this"}},
                ).json()["data"]

                self.assertTrue(fake_client.first_delta_sent.wait(timeout=3), "async provider delta was not forwarded live")
                live_events = client.get(started["eventsRef"]).json()["data"]["list"]
                fake_client.release_completion.set()
                terminal = _wait_for_result(client, started["resultRef"], "SUCCEEDED")

        self.assertEqual(fake_client.async_stream_calls, 1)
        self.assertEqual([event["payload"]["content"] for event in live_events if event["type"] == "llm_delta"], ["first "])
        self.assertEqual(terminal["output"]["answer"], "first second")

    def test_chatflow_v2_cancellation_stops_inflight_async_provider_stream(self) -> None:
        model_config_id = _seed_live_model_config(model_id="runtime-v2-cancellable-streaming-model")
        fake_client = _CancellableAsyncStreamingOpenAIClient()

        with patch("app.modules.workflow.domain.service.ProviderBackedOpenAIChatClient", lambda _config: fake_client):
            with TestClient(app) as client:
                chatflow = _create_llm_chatflow(client, llm_config={"modelConfigId": model_config_id})
                started = client.post(
                    f"/api/v1/chatflows/{chatflow['id']}/runs",
                    json={"input": {"sys.query": "cancel async stream"}},
                ).json()["data"]
                try:
                    self.assertTrue(fake_client.first_delta_sent.wait(timeout=3), "async provider did not begin")
                    cancelled = client.post(f"/api/v1/runtime-runs/{started['runId']}/cancel")
                    self.assertEqual(cancelled.status_code, 200, cancelled.text)
                    self.assertEqual(cancelled.json()["data"]["status"], "CANCELLED")
                    self.assertTrue(fake_client.cancelled.wait(timeout=1), "provider stream was not cancelled")
                    terminal = _wait_for_result(client, started["resultRef"], "CANCELLED")
                    events = client.get(started["eventsRef"]).json()["data"]["list"]
                finally:
                    fake_client.release.set()

        self.assertEqual(fake_client.async_stream_calls, 1)
        self.assertTrue(fake_client.closed.is_set())
        self.assertEqual(terminal["status"], "CANCELLED")
        self.assertEqual([event["type"] for event in events].count("llm_delta"), 1)
        self.assertNotIn("workflow_node_completed", [event["type"] for event in events])

    def test_chatflow_v2_cancellation_closes_real_provider_async_http_stream(self) -> None:
        model_config_id = _seed_live_model_config(model_id="runtime-v2-real-transport-cancellation-model")
        response = _CancellableAsyncHttpStreamResponse()
        http_client = _CancellableAsyncHttpClientFactory(response)

        with patch("app.modules.chat.domain.llm_request.httpx.AsyncClient", http_client):
            with TestClient(app) as client:
                chatflow = _create_llm_chatflow(client, llm_config={"modelConfigId": model_config_id})
                started = client.post(
                    f"/api/v1/chatflows/{chatflow['id']}/runs",
                    json={"input": {"sys.query": "cancel real async provider stream"}},
                ).json()["data"]
                try:
                    self.assertTrue(response.first_delta_sent.wait(timeout=3), "real provider did not emit a delta")
                    cancelled = client.post(f"/api/v1/runtime-runs/{started['runId']}/cancel")
                    self.assertEqual(cancelled.status_code, 200, cancelled.text)
                    self.assertTrue(response.closed.wait(timeout=1), "real provider HTTP stream was not closed")
                    terminal = _wait_for_result(client, started["resultRef"], "CANCELLED")
                    events = client.get(started["eventsRef"]).json()["data"]["list"]
                finally:
                    response.release.set()

        self.assertEqual(http_client.stream_count, 1)
        self.assertEqual(terminal["status"], "CANCELLED")
        self.assertEqual([event["type"] for event in events].count("llm_delta"), 1)
        self.assertNotIn("workflow_node_completed", [event["type"] for event in events])

    def test_chatflow_v2_non_stream_provider_does_not_synthesize_token_delta(self) -> None:
        model_config_id = _seed_live_model_config(model_id="runtime-v2-non-streaming-model")
        fake_client = _NonStreamingOpenAIClient(_assistant_payload("final only"))

        with patch("app.modules.workflow.domain.service.ProviderBackedOpenAIChatClient", lambda _config: fake_client):
            with TestClient(app) as client:
                chatflow = _create_llm_chatflow(client, llm_config={"modelConfigId": model_config_id})
                started = client.post(
                    f"/api/v1/chatflows/{chatflow['id']}/runs",
                    json={"input": {"sys.query": "non-stream this"}},
                ).json()["data"]
                terminal = _wait_for_result(client, started["resultRef"], "SUCCEEDED")
                events = client.get(started["eventsRef"]).json()["data"]["list"]

        self.assertEqual(terminal["output"]["answer"], "final only")
        self.assertFalse([event for event in events if event["type"] == "llm_delta"])
        self.assertEqual(fake_client.captured_payload["model"], "runtime-v2-non-streaming-model")

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


class _BlockingStreamingOpenAIClient(FakeOpenAIChatClient):
    def __init__(self, *, response_payload: dict[str, Any], chunks: list[str]) -> None:
        super().__init__(response_payload=response_payload)
        self._chunks = chunks
        self.first_delta_sent = threading.Event()
        self.release_completion = threading.Event()

    def stream_complete(self, payload: dict[str, Any], on_delta=None) -> dict[str, Any]:
        self.captured_payload = payload
        self.captured_payloads.append(payload)
        first, *rest = self._chunks
        if on_delta is not None:
            on_delta(first)
        self.first_delta_sent.set()
        if not self.release_completion.wait(timeout=3):
            raise AssertionError("test did not release streaming provider completion")
        if on_delta is not None:
            for chunk in rest:
                on_delta(chunk)
        if self._response_payload is None:
            raise AssertionError("streaming provider response payload is required")
        return self._response_payload


class _AsyncBlockingStreamingOpenAIClient:
    def __init__(self, *, response_payload: dict[str, Any], chunks: list[str]) -> None:
        self._response_payload = response_payload
        self._chunks = chunks
        self.first_delta_sent = threading.Event()
        self.release_completion = threading.Event()
        self.async_stream_calls = 0

    def complete(self, _payload: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError("Runtime V2 must use the async provider stream")

    async def stream_complete_async(self, _payload: dict[str, Any], on_delta=None) -> dict[str, Any]:
        self.async_stream_calls += 1
        first, *rest = self._chunks
        if on_delta is not None:
            on_delta(first)
        self.first_delta_sent.set()
        if not await asyncio.to_thread(self.release_completion.wait, 3):
            raise AssertionError("test did not release async streaming provider completion")
        if on_delta is not None:
            for chunk in rest:
                on_delta(chunk)
        return self._response_payload


class _CancellableAsyncStreamingOpenAIClient:
    def __init__(self) -> None:
        self.first_delta_sent = threading.Event()
        self.release = threading.Event()
        self.cancelled = threading.Event()
        self.closed = threading.Event()
        self.async_stream_calls = 0

    async def stream_complete_async(self, _payload: dict[str, Any], on_delta=None) -> dict[str, Any]:
        self.async_stream_calls += 1
        if on_delta is not None:
            on_delta("first ")
        self.first_delta_sent.set()
        try:
            await asyncio.to_thread(self.release.wait, 3)
        except asyncio.CancelledError:
            self.cancelled.set()
            raise
        finally:
            self.closed.set()
        return _assistant_payload("should not complete")


class _CancellableAsyncHttpClientFactory:
    def __init__(self, response: "_CancellableAsyncHttpStreamResponse") -> None:
        self._response = response
        self.stream_count = 0

    def __call__(self, **_kwargs: object) -> "_CancellableAsyncHttpClientFactory":
        return self

    async def __aenter__(self) -> "_CancellableAsyncHttpClientFactory":
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    def stream(self, *_args: object, **_kwargs: object) -> "_CancellableAsyncHttpStreamResponse":
        self.stream_count += 1
        return self._response


class _CancellableAsyncHttpStreamResponse:
    def __init__(self) -> None:
        self.first_delta_sent = threading.Event()
        self.release = threading.Event()
        self.closed = threading.Event()
        self.status_code = 200

    async def __aenter__(self) -> "_CancellableAsyncHttpStreamResponse":
        return self

    async def __aexit__(self, *_args: object) -> None:
        self.closed.set()

    async def aiter_lines(self):
        yield 'data: {"choices":[{"delta":{"content":"first "}}]}'
        self.first_delta_sent.set()
        await asyncio.to_thread(self.release.wait, 3)
        yield "data: [DONE]"

    async def aread(self) -> bytes:
        return b""


class _NonStreamingOpenAIClient:
    def __init__(self, response_payload: dict[str, Any]) -> None:
        self._response_payload = response_payload
        self.captured_payload: dict[str, Any] = {}

    def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.captured_payload = payload
        return self._response_payload


if __name__ == "__main__":
    unittest.main()
