from dataclasses import dataclass
import re
from time import monotonic
from typing import Any

from app.modules.chat.domain.llm_request import (
    ChatRequestMessage,
    OpenAIChatRequestBuilder,
    ProviderBackedOpenAIChatClient,
    ProviderChatConfig,
)


@dataclass(frozen=True)
class ProviderModelConnectivityResult:
    ok: bool
    model: str
    elapsed_ms: int
    usage: dict[str, int]
    reply_preview: str | None
    error: str | None

    def to_response(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "model": self.model,
            "elapsedMs": self.elapsed_ms,
            "usage": self.usage,
            "replyPreview": self.reply_preview,
            "error": self.error,
        }


class ProviderModelConnectivityTester:
    def test(self, model_config: dict[str, Any]) -> ProviderModelConnectivityResult:
        started_at = monotonic()
        model = str(model_config["model_id"])
        provider_config = ProviderChatConfig(
            provider_type=str(model_config["provider_type"]),
            base_url=str(model_config["provider_base_url"]),
            auth_config=dict(model_config["provider_auth_config"] or {}),
        )
        payload = OpenAIChatRequestBuilder().build(
            model=model,
            messages=[ChatRequestMessage(role="user", content="1")],
            temperature=0,
            max_tokens=8,
        )
        try:
            response = ProviderBackedOpenAIChatClient(
                provider_config,
                timeout=30,
                max_attempts=1,
            ).complete(payload)
        except Exception as exc:
            return ProviderModelConnectivityResult(
                ok=False,
                model=model,
                elapsed_ms=_elapsed_ms(started_at),
                usage=_usage_from_response({}),
                reply_preview=None,
                error=_safe_error(str(exc), provider_config.auth_config),
            )

        return ProviderModelConnectivityResult(
            ok=True,
            model=model,
            elapsed_ms=_elapsed_ms(started_at),
            usage=_usage_from_response(response),
            reply_preview=_reply_preview(response),
            error=None,
        )


def _elapsed_ms(started_at: float) -> int:
    return max(0, int((monotonic() - started_at) * 1000))


def _usage_from_response(response: dict[str, Any]) -> dict[str, int]:
    usage = response.get("usage")
    if not isinstance(usage, dict):
        usage = {}
    input_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or input_tokens + output_tokens)
    return {
        "inputTokens": input_tokens,
        "outputTokens": output_tokens,
        "totalTokens": total_tokens,
    }


def _reply_preview(response: dict[str, Any]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if content is None:
        return ""
    return str(content)[:200]


def _safe_error(message: str, auth_config: dict[str, Any]) -> str:
    sanitized = message
    for key in ("api_key", "apiKey"):
        secret = str(auth_config.get(key) or "")
        if secret:
            sanitized = sanitized.replace(secret, "[redacted]")
    return re.sub(r"sk-[A-Za-z0-9._-]+", "[redacted]", sanitized)
