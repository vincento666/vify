from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Mapping


@dataclass(frozen=True)
class NormalizedModelUsage:
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int | None
    cache_write_tokens: int | None
    reasoning_tokens: int | None
    total_tokens: int
    usage_source: str
    provider_cost_usd: Decimal | None

    def as_record_values(self) -> dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_write_tokens": self.cache_write_tokens,
            "reasoning_tokens": self.reasoning_tokens,
            "total_tokens": self.total_tokens,
            "usage_source": self.usage_source,
            "provider_cost_usd": self.provider_cost_usd,
        }


def normalize_model_usage(raw: Mapping[str, Any] | None) -> NormalizedModelUsage:
    payload = dict(raw or {})
    prompt_details = _mapping(payload.get("prompt_tokens_details") or payload.get("input_tokens_details"))
    completion_details = _mapping(
        payload.get("completion_tokens_details") or payload.get("output_tokens_details")
    )
    input_tokens = _required_token(payload, "inputTokens", "input_tokens", "prompt_tokens", "promptTokens")
    output_tokens = _required_token(
        payload,
        "outputTokens",
        "output_tokens",
        "completion_tokens",
        "completionTokens",
    )
    provider_total = _optional_token(payload, "totalTokens", "total_tokens")
    cache_read_tokens = _optional_token(
        payload,
        "cacheReadTokens",
        "cache_read_tokens",
        "cached_tokens",
    )
    if cache_read_tokens is None:
        cache_read_tokens = _optional_token(prompt_details, "cached_tokens", "cache_read_tokens")
    cache_write_tokens = _optional_token(
        payload,
        "cacheWriteTokens",
        "cache_write_tokens",
    )
    if cache_write_tokens is None:
        cache_write_tokens = _optional_token(prompt_details, "cache_write_tokens")
    reasoning_tokens = _optional_token(payload, "reasoningTokens", "reasoning_tokens")
    if reasoning_tokens is None:
        reasoning_tokens = _optional_token(completion_details, "reasoning_tokens")
    total_tokens = provider_total if provider_total is not None else input_tokens + output_tokens
    return NormalizedModelUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read_tokens,
        cache_write_tokens=cache_write_tokens,
        reasoning_tokens=reasoning_tokens,
        total_tokens=total_tokens,
        usage_source="provider" if payload else "unknown",
        provider_cost_usd=_optional_decimal(
            payload,
            "providerCostUsd",
            "provider_cost_usd",
            "cost_usd",
            "cost",
        ),
    )


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _required_token(payload: Mapping[str, Any], *keys: str) -> int:
    value = _optional_token(payload, *keys)
    return value if value is not None else 0


def _optional_token(payload: Mapping[str, Any], *keys: str) -> int | None:
    for key in keys:
        if key not in payload or payload[key] is None:
            continue
        raw = payload[key]
        if isinstance(raw, bool):
            raise ValueError("model usage tokens must be integers")
        if isinstance(raw, int):
            value = raw
        elif isinstance(raw, str) and re.fullmatch(r"-?\d+", raw.strip()):
            value = int(raw)
        else:
            raise ValueError("model usage tokens must be integers")
        if value < 0:
            raise ValueError("model usage tokens must be non-negative")
        return value
    return None


def _optional_decimal(payload: Mapping[str, Any], *keys: str) -> Decimal | None:
    for key in keys:
        if key not in payload or payload[key] is None:
            continue
        try:
            value = Decimal(str(payload[key]))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("model usage cost must be a decimal") from exc
        if not value.is_finite():
            raise ValueError("model usage cost must be finite")
        if value < 0:
            raise ValueError("model usage cost must be non-negative")
        return value
    return None
