import asyncio
import threading
import unittest
from time import monotonic
from typing import Callable
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

    def test_stream_preserves_openrouter_reasoning_outside_visible_content(self) -> None:
        client_factory = _HttpClientFactory(
            [
                _HttpStreamResponse(
                    [
                        'data: {"choices":[{"delta":{"reasoning":"思考A"}}]}',
                        'data: {"choices":[{"delta":{"reasoning_details":[{"type":"reasoning.text","text":"思考B"}]}}]}',
                        'data: {"choices":[{"delta":{"content":"正文A"}}]}',
                        'data: {"choices":[{"delta":{"content":"正文B"},"finish_reason":"stop"}],"usage":{"total_tokens":4}}',
                        "data: [DONE]",
                    ]
                )
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
        deltas: list[str] = []

        with patch("app.modules.chat.domain.llm_request.httpx.Client", client_factory):
            response = llm_client.stream_complete({"model": "model", "messages": []}, on_delta=deltas.append)

        message = response["choices"][0]["message"]
        self.assertEqual(message["content"], "正文A正文B")
        self.assertEqual(message["reasoning"], "思考A思考B")
        self.assertEqual(deltas, ["正文A", "正文B"])

    def test_stream_does_not_retry_after_a_visible_provider_delta(self) -> None:
        client_factory = _HttpClientFactory(
            [
                _PartialFailureStreamResponse('data: {"choices":[{"delta":{"content":"A"}}]}'),
                _HttpStreamResponse(
                    [
                        'data: {"choices":[{"delta":{"content":"A"}}]}',
                        'data: {"choices":[{"delta":{"content":"B"},"finish_reason":"stop"}]}',
                        "data: [DONE]",
                    ]
                ),
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
        deltas: list[str] = []

        with patch("app.modules.chat.domain.llm_request.httpx.Client", client_factory):
            with self.assertRaises(httpx.TransportError):
                llm_client.stream_complete({"model": "model", "messages": []}, on_delta=deltas.append)

        self.assertEqual(deltas, ["A"])
        self.assertEqual(client_factory.stream_count, 1)


class ProviderBackedOpenAIChatClientAsyncTransportTest(unittest.IsolatedAsyncioTestCase):
    async def test_async_stream_delivers_incremental_text_before_final_response(self) -> None:
        client_factory = _AsyncHttpClientFactory(
            [
                _AsyncHttpStreamResponse(
                    [
                        'data: {"choices":[{"delta":{"content":"正文A"}}]}',
                        'data: {"choices":[{"delta":{"content":"正文B"},"finish_reason":"stop"}]}',
                        "data: [DONE]",
                    ]
                )
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
        deltas: list[str] = []

        with patch("app.modules.chat.domain.llm_request.httpx.AsyncClient", client_factory):
            response = await llm_client.stream_complete_async(
                {"model": "model", "messages": []},
                on_delta=deltas.append,
            )

        self.assertEqual(deltas, ["正文A", "正文B"])
        self.assertEqual(response["choices"][0]["message"]["content"], "正文A正文B")
        self.assertEqual(client_factory.stream_count, 1)
        self.assertEqual(client_factory.init_kwargs["timeout"], 60.0)

    async def test_async_stream_enforces_configured_concurrency_limit(self) -> None:
        first_started = asyncio.Event()
        release_first = asyncio.Event()
        client_factory = _AsyncHttpClientFactory(
            [
                _AsyncBlockingHttpStreamResponse(
                    ['data: {"choices":[{"delta":{"content":"A"}}]}', "data: [DONE]"],
                    first_started,
                    release_first,
                ),
                _AsyncHttpStreamResponse(
                    ['data: {"choices":[{"delta":{"content":"B"}}]}', "data: [DONE]"]
                ),
            ]
        )
        llm_client = ProviderBackedOpenAIChatClient(
            ProviderChatConfig(
                provider_type="OPENAI",
                base_url="https://openrouter.ai/api/v1",
                auth_config={"api_key": "test-key"},
            ),
            retry_sleep=0,
            max_concurrent_streams=1,
        )

        with patch("app.modules.chat.domain.llm_request.httpx.AsyncClient", client_factory):
            first = asyncio.create_task(llm_client.stream_complete_async({"model": "model", "messages": []}))
            await asyncio.wait_for(first_started.wait(), timeout=1)
            second = asyncio.create_task(llm_client.stream_complete_async({"model": "model", "messages": []}))
            await asyncio.sleep(0.05)
            self.assertEqual(client_factory.stream_count, 1)
            release_first.set()
            await asyncio.gather(first, second)

        self.assertEqual(client_factory.stream_count, 2)

    async def test_async_stream_does_not_retry_after_visible_provider_delta(self) -> None:
        client_factory = _AsyncHttpClientFactory(
            [
                _AsyncPartialFailureStreamResponse('data: {"choices":[{"delta":{"content":"A"}}]}'),
                _AsyncHttpStreamResponse(
                    [
                        'data: {"choices":[{"delta":{"content":"A"}}]}',
                        'data: {"choices":[{"delta":{"content":"B"}}]}',
                        "data: [DONE]",
                    ]
                ),
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
        deltas: list[str] = []

        with patch("app.modules.chat.domain.llm_request.httpx.AsyncClient", client_factory):
            with self.assertRaises(httpx.TransportError):
                await llm_client.stream_complete_async({"model": "model", "messages": []}, on_delta=deltas.append)

        self.assertEqual(deltas, ["A"])
        self.assertEqual(client_factory.stream_count, 1)

    async def test_async_stream_propagates_cancellation_and_closes_response(self) -> None:
        started = asyncio.Event()
        release = asyncio.Event()
        response = _AsyncBlockingHttpStreamResponse(
            ['data: {"choices":[{"delta":{"content":"A"}}]}', "data: [DONE]"],
            started,
            release,
        )
        client_factory = _AsyncHttpClientFactory([response])
        llm_client = ProviderBackedOpenAIChatClient(
            ProviderChatConfig(
                provider_type="OPENAI",
                base_url="https://openrouter.ai/api/v1",
                auth_config={"api_key": "test-key"},
            ),
            retry_sleep=0,
        )

        with patch("app.modules.chat.domain.llm_request.httpx.AsyncClient", client_factory):
            task = asyncio.create_task(llm_client.stream_complete_async({"model": "model", "messages": []}))
            await asyncio.wait_for(started.wait(), timeout=1)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task

        self.assertTrue(response.closed)


class ProviderBackedOpenAIChatClientCrossLoopConcurrencyTest(unittest.TestCase):
    def test_async_stream_concurrency_limit_is_safe_across_worker_event_loops(self) -> None:
        first_started = threading.Event()
        release_first = threading.Event()
        client_factory = _CrossLoopAsyncHttpClientFactory(first_started, release_first)
        llm_client = ProviderBackedOpenAIChatClient(
            ProviderChatConfig(
                provider_type="OPENAI",
                base_url="https://openrouter.ai/api/v1",
                auth_config={"api_key": "test-key"},
            ),
            retry_sleep=0,
            max_concurrent_streams=1,
        )
        errors: list[BaseException] = []

        def run_stream() -> None:
            try:
                asyncio.run(llm_client.stream_complete_async({"model": "model", "messages": []}))
            except BaseException as exc:  # pragma: no cover - asserted below
                errors.append(exc)

        with patch("app.modules.chat.domain.llm_request.httpx.AsyncClient", client_factory):
            first = threading.Thread(target=run_stream, daemon=True)
            first.start()
            self.assertTrue(first_started.wait(timeout=1))
            second = threading.Thread(target=run_stream, daemon=True)
            second.start()
            self.assertTrue(_wait_for(lambda: client_factory.stream_count == 1))
            release_first.set()
            first.join(timeout=1)
            second.join(timeout=1)

        self.assertFalse(first.is_alive(), "first worker loop did not finish")
        self.assertFalse(second.is_alive(), "second worker loop did not resume after slot release")
        self.assertEqual(errors, [])
        self.assertEqual(client_factory.stream_count, 2)


class _HttpClientFactory:
    def __init__(self, outcomes: list[object]) -> None:
        self._outcomes = outcomes
        self.post_count = 0
        self.stream_count = 0
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

    def stream(self, *_args: object, **kwargs: object) -> "_HttpStreamResponse":
        self.stream_count += 1
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


class _HttpStreamResponse:
    def __init__(self, lines: list[str], status_code: int = 200, text: str = "") -> None:
        self.status_code = status_code
        self._lines = lines
        self._text = text

    def __enter__(self) -> "_HttpStreamResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def iter_lines(self) -> list[str]:
        return self._lines

    def read(self) -> bytes:
        return self._text.encode()


class _PartialFailureStreamResponse(_HttpStreamResponse):
    def __init__(self, first_line: str) -> None:
        super().__init__([first_line])

    def iter_lines(self):  # type: ignore[override]
        yield self._lines[0]
        raise httpx.ReadError("stream reset after first delta")


class _AsyncHttpClientFactory:
    def __init__(self, outcomes: list[object]) -> None:
        self._outcomes = outcomes
        self.stream_count = 0
        self.init_kwargs: dict[str, object] = {}

    def __call__(self, **kwargs: object) -> "_AsyncHttpClientFactory":
        self.init_kwargs = kwargs
        return self

    async def __aenter__(self) -> "_AsyncHttpClientFactory":
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    def stream(self, *_args: object, **_kwargs: object) -> "_AsyncHttpStreamResponse":
        self.stream_count += 1
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        assert isinstance(outcome, _AsyncHttpStreamResponse)
        return outcome


class _AsyncHttpStreamResponse:
    def __init__(self, lines: list[str], status_code: int = 200, text: str = "") -> None:
        self.status_code = status_code
        self._lines = lines
        self._text = text

    async def __aenter__(self) -> "_AsyncHttpStreamResponse":
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def aiter_lines(self):
        for line in self._lines:
            yield line

    async def aread(self) -> bytes:
        return self._text.encode()


class _AsyncBlockingHttpStreamResponse(_AsyncHttpStreamResponse):
    def __init__(self, lines: list[str], started: asyncio.Event, release: asyncio.Event) -> None:
        super().__init__(lines)
        self._started = started
        self._release = release
        self.closed = False

    async def __aexit__(self, *_args: object) -> None:
        self.closed = True

    async def aiter_lines(self):
        for index, line in enumerate(self._lines):
            if index == 0:
                self._started.set()
                await self._release.wait()
            yield line


class _AsyncPartialFailureStreamResponse(_AsyncHttpStreamResponse):
    def __init__(self, first_line: str) -> None:
        super().__init__([first_line])

    async def aiter_lines(self):
        yield self._lines[0]
        raise httpx.ReadError("stream reset after first delta")


class _CrossLoopAsyncHttpClientFactory:
    def __init__(self, first_started: threading.Event, release_first: threading.Event) -> None:
        self._first_started = first_started
        self._release_first = release_first
        self._lock = threading.Lock()
        self.stream_count = 0

    def __call__(self, **_kwargs: object) -> "_CrossLoopAsyncHttpClientFactory":
        return self

    async def __aenter__(self) -> "_CrossLoopAsyncHttpClientFactory":
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    def stream(self, *_args: object, **_kwargs: object) -> "_AsyncHttpStreamResponse":
        with self._lock:
            self.stream_count += 1
            if self.stream_count == 1:
                return _CrossLoopBlockingHttpStreamResponse(self._first_started, self._release_first)
        return _AsyncHttpStreamResponse(['data: {"choices":[{"delta":{"content":"B"}}]}', "data: [DONE]"])


class _CrossLoopBlockingHttpStreamResponse(_AsyncHttpStreamResponse):
    def __init__(self, started: threading.Event, release: threading.Event) -> None:
        super().__init__(['data: {"choices":[{"delta":{"content":"A"}}]}', "data: [DONE]"])
        self._started = started
        self._release = release

    async def aiter_lines(self):
        self._started.set()
        await asyncio.to_thread(self._release.wait)
        for line in self._lines:
            yield line


def _wait_for(predicate: Callable[[], bool], timeout: float = 1.0) -> bool:
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        if predicate():
            return True
    return False


if __name__ == "__main__":
    unittest.main()
