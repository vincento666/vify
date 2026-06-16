import unittest

import httpx

from app.modules.chat.domain.llm_request import OpenAIChatRequestBuilder
from app.modules.provider.api.schemas import ModelConfigDto
from app.modules.provider.infra.llm_adapters import OpenAIAdapterParser
from app.modules.workflow.domain.context import ExecutionContext
from app.modules.workflow.domain.engine import LlmNodeExecutor, WorkflowExecutionError
from app.modules.workflow.domain.service import _AgentBackedWorkflowLlmCompleter


class RecordingLlmCompleter:
    def __init__(self) -> None:
        self.prompts: list[str] = []
        self.options: list[dict[str, object] | None] = []

    def complete_prompt(self, prompt: str, _options: dict[str, object] | None = None) -> str:
        self.prompts.append(prompt)
        self.options.append(_options)
        return f"real llm: {prompt}"


class UsageRecordingLlmCompleter(RecordingLlmCompleter):
    def __init__(self) -> None:
        super().__init__()
        self._debug = {
            "model": "debug-model",
            "elapsedMs": 37,
            "input": {"messages": [{"role": "user", "content": "User: reset password"}]},
            "output": {"content": "real llm: User: reset password"},
            "usage": {"inputTokens": 12, "outputTokens": 8, "totalTokens": 20, "estimated": False},
        }

    def consume_last_call_debug(self) -> dict[str, object]:
        debug = dict(self._debug)
        self._debug = {}
        return debug


class LlmNodeCompleterTest(unittest.TestCase):
    def test_llm_node_uses_injected_completer_when_available(self) -> None:
        completer = RecordingLlmCompleter()
        context = ExecutionContext()
        context.set_output("start", {"userMessage": "reset password"})

        result = LlmNodeExecutor(completer).execute(
            {
                "node_key": "llm",
                "type": "LLM",
                "config": {"prompt": "User: {{start.userMessage}}", "outputVariable": "answer"},
            },
            context,
        )

        self.assertEqual(result["answer"], "real llm: User: reset password")
        self.assertEqual(
            result["events"],
            [
                {"type": "llm_delta", "nodeKey": "llm", "content": "real llm: User: reset password"},
                {"type": "message_done", "nodeKey": "llm", "content": "real llm: User: reset password"},
            ],
        )
        self.assertEqual(completer.prompts, ["User: reset password"])

    def test_llm_node_renders_local_input_variables_in_system_and_user_prompts(self) -> None:
        completer = RecordingLlmCompleter()
        context = ExecutionContext()
        context.set_output("start", {"USER_INPUT": "refund status"})

        result = LlmNodeExecutor(completer).execute(
            {
                "node_key": "llm_1",
                "type": "LLM",
                "config": {
                    "systemPrompt": "You answer {{input}}",
                    "prompt": "User asked {{input}}",
                    "inputParameters": [
                        {"name": "input", "type": "string", "valueMode": "reference", "value": "{{start.USER_INPUT}}"}
                    ],
                    "outputVariable": "answer",
                },
            },
            context,
        )

        self.assertEqual(completer.prompts, ["User asked refund status"])
        self.assertEqual(completer.options[0], {"systemPrompt": "You answer refund status"})
        self.assertNotIn("{{input}}", result["answer"])

    def test_llm_node_projects_debug_usage_into_output_and_events(self) -> None:
        completer = UsageRecordingLlmCompleter()
        context = ExecutionContext()
        context.set_output("start", {"userMessage": "reset password"})

        result = LlmNodeExecutor(completer).execute(
            {
                "node_key": "llm",
                "type": "LLM",
                "config": {"prompt": "User: {{start.userMessage}}", "outputVariable": "answer"},
            },
            context,
        )

        self.assertEqual(result["__usage"], {"inputTokens": 12, "outputTokens": 8, "totalTokens": 20, "estimated": False})
        self.assertEqual(result["__debug"]["llm"]["model"], "debug-model")
        self.assertEqual(
            result["events"][-1],
            {"type": "node_usage", "nodeKey": "llm", "inputTokens": 12, "outputTokens": 8, "totalTokens": 20},
        )

    def test_llm_stream_events_survive_declared_output_parameters(self) -> None:
        context = ExecutionContext()

        result = LlmNodeExecutor().execute(
            {
                "node_key": "llm",
                "type": "LLM",
                "config": {
                    "prompt": "hello",
                    "outputVariable": "answer",
                    "outputParameters": [{"name": "answer", "type": "string"}],
                },
            },
            context,
        )

        self.assertEqual(result["answer"], "LLM mock: hello")
        self.assertEqual([event["type"] for event in result["events"]], ["llm_delta", "message_done"])

    def test_agent_backed_completer_wraps_provider_network_failure(self) -> None:
        completer = _AgentBackedWorkflowLlmCompleter(
            agent={"system_prompt": "", "temperature": 0.1, "max_tokens": 64},
            model_config=ModelConfigDto(
                id=1,
                provider_id=1,
                provider_type="OPENAI",
                provider_base_url="https://invalid.local",
                provider_auth_config={},
                name="Demo",
                model_id="demo",
                context_size=4096,
                extra_params={},
            ),
            model_facade=None,
            request_builder=OpenAIChatRequestBuilder(),
            parser=OpenAIAdapterParser(),
            llm_client_factory=lambda _config: _FailingLlmClient(),
        )

        with self.assertRaises(WorkflowExecutionError) as raised:
            completer.complete_prompt("hello")

        self.assertIn("LLM provider request failed", str(raised.exception))
        self.assertIn("模型服务网络不可达", str(raised.exception))
        self.assertNotIn("nodename nor servname", str(raised.exception))

    def test_agent_backed_completer_resolves_model_string_to_model_config(self) -> None:
        client_factory = _RecordingClientFactory()
        completer = _AgentBackedWorkflowLlmCompleter(
            agent={"system_prompt": "", "temperature": 0.1, "max_tokens": 64},
            model_config=ModelConfigDto(
                id=1,
                provider_id=1,
                provider_type="OPENAI",
                provider_base_url="https://default.invalid/v1",
                provider_auth_config={},
                name="Default",
                model_id="default-model",
                context_size=4096,
                extra_params={},
            ),
            model_facade=_ModelLookupFacade(),
            request_builder=OpenAIChatRequestBuilder(),
            parser=OpenAIAdapterParser(),
            llm_client_factory=client_factory,
        )

        result = completer.complete_prompt("hello", {"model": "xiaomi/mimo-v2-flash"})

        self.assertEqual(result, "ok")
        self.assertEqual(client_factory.base_urls, ["https://openrouter.ai/api/v1"])
        self.assertEqual(client_factory.payloads[0]["model"], "xiaomi/mimo-v2-flash")

    def test_agent_backed_completer_records_sanitized_fallback_attempts(self) -> None:
        client_factory = _FallbackClientFactory()
        completer = _AgentBackedWorkflowLlmCompleter(
            agent={"system_prompt": "", "temperature": 0.1, "max_tokens": 64},
            model_config=ModelConfigDto(
                id=1,
                provider_id=1,
                provider_type="OPENAI",
                provider_base_url="https://openrouter.ai/api/v1",
                provider_auth_config={"api_key": "integration-test-key"},
                name="Primary",
                model_id="primary-model",
                context_size=4096,
                extra_params={"fallbackModel": "fallback-model"},
            ),
            model_facade=None,
            request_builder=OpenAIChatRequestBuilder(),
            parser=OpenAIAdapterParser(),
            llm_client_factory=client_factory,
        )

        result = completer.complete_prompt("hello")
        debug = completer.consume_last_call_debug()

        self.assertEqual(result, "fallback ok")
        self.assertEqual(client_factory.payload_models, ["primary-model", "fallback-model"])
        self.assertEqual(debug["model"], "fallback-model")
        self.assertEqual(
            debug["fallback"],
            {
                "attempted": True,
                "attempts": [
                    {
                        "model": "primary-model",
                        "status": "failed",
                        "reason": "模型服务网络不可达，请检查模型服务 Base URL、网络/DNS 或代理配置",
                    },
                    {"model": "fallback-model", "status": "succeeded"},
                ],
            },
        )


class _FailingLlmClient:
    def complete(self, _payload: dict[str, object]) -> dict[str, object]:
        raise httpx.ConnectError("[Errno 8] nodename nor servname provided, or not known")


class _RecordingClientFactory:
    def __init__(self) -> None:
        self.base_urls: list[str] = []
        self.payloads: list[dict[str, object]] = []

    def __call__(self, config: object) -> "_RecordingClientFactory":
        self.base_urls.append(str(getattr(config, "base_url")))
        return self

    def complete(self, payload: dict[str, object]) -> dict[str, object]:
        self.payloads.append(payload)
        return {
            "choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
            "usage": {"total_tokens": 1},
        }


class _FallbackClientFactory:
    def __init__(self) -> None:
        self.payload_models: list[str] = []

    def __call__(self, _config: object) -> "_FallbackClientFactory":
        return self

    def complete(self, payload: dict[str, object]) -> dict[str, object]:
        model = str(payload["model"])
        self.payload_models.append(model)
        if model == "primary-model":
            raise httpx.ConnectError("[Errno 8] nodename nor servname provided, or not known")
        return {
            "choices": [{"message": {"role": "assistant", "content": "fallback ok"}, "finish_reason": "stop"}],
            "usage": {"total_tokens": 2},
        }


class _ModelLookupFacade:
    def get_enabled_model_config(self, model_config_id: int) -> ModelConfigDto:
        raise AssertionError(f"unexpected id lookup: {model_config_id}")

    def find_enabled_model_config_by_model_id(self, model_id: str) -> ModelConfigDto | None:
        if model_id != "xiaomi/mimo-v2-flash":
            return None
        return ModelConfigDto(
            id=607,
            provider_id=665,
            provider_type="OPENAI",
            provider_base_url="https://openrouter.ai/api/v1",
            provider_auth_config={"api_key": "integration-test-key"},
            name="Xiaomi MiMo v2 Flash",
            model_id=model_id,
            context_size=128000,
            extra_params={},
        )


if __name__ == "__main__":
    unittest.main()
