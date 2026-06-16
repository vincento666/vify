import unittest
from unittest.mock import patch

import httpx

from app.modules.chat.domain.llm_request import ProviderBackedOpenAIChatClient, ProviderChatConfig


class ProviderBackedOpenAIChatClientTest(unittest.TestCase):
    def test_retries_transient_transport_errors_before_returning_response(self) -> None:
        client_factory = _HttpClientFactory(
            [
                httpx.ConnectError("tls eof"),
                _HttpResponse(200, {"choices": [{"message": {"content": "ok"}}]}),
            ]
        )
        llm_client = ProviderBackedOpenAIChatClient(
            ProviderChatConfig(
                provider_type="OPENAI",
                base_url="https://openrouter.ai/api/v1",
                auth_config={"api_key": "test-key"},
            ),
            retry_sleep=0,
        )

        with patch("app.modules.chat.domain.llm_request.httpx.Client", client_factory):
            response = llm_client.complete({"model": "model", "messages": []})

        self.assertEqual(response["choices"][0]["message"]["content"], "ok")
        self.assertEqual(client_factory.post_count, 2)
        self.assertEqual(client_factory.init_kwargs["trust_env"], True)

    def test_resolves_api_key_from_env_ref(self) -> None:
        client_factory = _HttpClientFactory(
            [_HttpResponse(200, {"choices": [{"message": {"content": "ok"}}]})]
        )
        llm_client = ProviderBackedOpenAIChatClient(
            ProviderChatConfig(
                provider_type="OPENAI",
                base_url="https://openrouter.ai/api/v1",
                auth_config={"api_key_ref": "env:HIFY_TEST_LLM_KEY"},
            ),
            retry_sleep=0,
        )

        with (
            patch.dict("os.environ", {"HIFY_TEST_LLM_KEY": "sk-env-test"}, clear=False),
            patch("app.modules.chat.domain.llm_request.httpx.Client", client_factory),
        ):
            response = llm_client.complete({"model": "model", "messages": []})

        self.assertEqual(response["choices"][0]["message"]["content"], "ok")
        self.assertEqual(client_factory.headers["Authorization"], "Bearer sk-env-test")


class _HttpClientFactory:
    def __init__(self, outcomes: list[object]) -> None:
        self._outcomes = outcomes
        self.post_count = 0
        self.init_kwargs: dict[str, object] = {}
        self.headers: dict[str, str] = {}

    def __call__(self, **kwargs: object) -> "_HttpClientFactory":
        self.init_kwargs = kwargs
        return self

    def __enter__(self) -> "_HttpClientFactory":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def post(self, *_args: object, **kwargs: object) -> "_HttpResponse":
        self.post_count += 1
        self.headers = dict(kwargs.get("headers") or {})
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class _HttpResponse:
    def __init__(self, status_code: int, payload: dict[str, object]) -> None:
        self.status_code = status_code
        self.text = str(payload)
        self._payload = payload

    def json(self) -> dict[str, object]:
        return self._payload


if __name__ == "__main__":
    unittest.main()
