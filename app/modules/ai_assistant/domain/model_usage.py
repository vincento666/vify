from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import json
import os
import re
from typing import Any, Mapping


@dataclass(frozen=True)
class NormalizedModelUsage:
    input_tokens: int | None
    output_tokens: int | None
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
        }


@dataclass(frozen=True)
class ModelPrice:
    input_usd_per_million: Decimal
    output_usd_per_million: Decimal
    cache_read_usd_per_million: Decimal | None = None
    cache_write_usd_per_million: Decimal | None = None


@dataclass(frozen=True)
class CostResolution:
    provider_cost_usd: Decimal | None
    estimated_cost_usd: Decimal | None
    effective_cost_usd: Decimal | None
    cost_source: str
    pricing_version: str | None


class VersionedCostResolver:
    def __init__(
        self,
        *,
        version: str,
        prices: Mapping[tuple[str, str], ModelPrice],
    ) -> None:
        self._version = version
        self._prices = dict(prices)

    def resolve(
        self,
        provider: str,
        model: str,
        usage: NormalizedModelUsage,
    ) -> CostResolution:
        if usage.provider_cost_usd is not None:
            actual = _cost_decimal(usage.provider_cost_usd)
            return CostResolution(actual, None, actual, "provider", None)
        price = self._prices.get((provider, model))
        if price is None or usage.input_tokens is None or usage.output_tokens is None:
            return CostResolution(None, None, None, "unknown", None)
        cache_read = usage.cache_read_tokens or 0
        cache_write = usage.cache_write_tokens or 0
        regular_input = usage.input_tokens
        priced_cache_read = 0
        priced_cache_write = 0
        if price.cache_read_usd_per_million is not None:
            priced_cache_read = min(cache_read, regular_input)
            regular_input -= priced_cache_read
        if price.cache_write_usd_per_million is not None:
            priced_cache_write = min(cache_write, regular_input)
            regular_input -= priced_cache_write
        estimated = Decimal(regular_input) * price.input_usd_per_million
        if price.cache_read_usd_per_million is not None:
            estimated += Decimal(priced_cache_read) * price.cache_read_usd_per_million
        if price.cache_write_usd_per_million is not None:
            estimated += Decimal(priced_cache_write) * price.cache_write_usd_per_million
        estimated += Decimal(usage.output_tokens) * price.output_usd_per_million
        estimated = _cost_decimal(estimated / Decimal(1_000_000))
        return CostResolution(None, estimated, estimated, "price_table", self._version)


def configured_cost_resolver() -> VersionedCostResolver:
    raw = os.getenv("HIFY_AI_ASSISTANT_MODEL_PRICES_JSON", "").strip()
    if not raw:
        return VersionedCostResolver(version="unconfigured", prices={})
    payload = json.loads(raw)
    if not isinstance(payload, Mapping):
        raise ValueError("model price configuration must be an object")
    version = str(payload.get("version") or "").strip()
    if not version:
        raise ValueError("model price configuration requires a version")
    if len(version) > 120:
        raise ValueError("model price version exceeds 120 characters")
    raw_prices = payload.get("prices")
    if not isinstance(raw_prices, Mapping):
        raise ValueError("model price configuration requires prices")
    prices: dict[tuple[str, str], ModelPrice] = {}
    for identity, raw_price in raw_prices.items():
        if not isinstance(identity, str) or ":" not in identity or not isinstance(raw_price, Mapping):
            raise ValueError("model price identity must be provider:model")
        provider, model = identity.split(":", 1)
        if not provider or not model:
            raise ValueError("model price identity requires provider and model")
        if len(provider) > 120 or len(model) > 240:
            raise ValueError("model price identity exceeds storage limits")
        prices[(provider, model)] = ModelPrice(
            input_usd_per_million=_price_decimal(raw_price, "inputUsdPerMillion"),
            output_usd_per_million=_price_decimal(raw_price, "outputUsdPerMillion"),
            cache_read_usd_per_million=_optional_price_decimal(
                raw_price,
                "cacheReadUsdPerMillion",
            ),
            cache_write_usd_per_million=_optional_price_decimal(
                raw_price,
                "cacheWriteUsdPerMillion",
            ),
        )
    return VersionedCostResolver(version=version, prices=prices)


def resolve_configured_model_cost(
    provider: str,
    model: str,
    usage: NormalizedModelUsage,
) -> CostResolution:
    if usage.provider_cost_usd is not None:
        actual = _cost_decimal(usage.provider_cost_usd)
        return CostResolution(actual, None, actual, "provider", None)
    return configured_cost_resolver().resolve(provider, model, usage)


def normalize_model_usage(raw: Mapping[str, Any] | None) -> NormalizedModelUsage:
    payload = dict(raw or {})
    prompt_details = _mapping(payload.get("prompt_tokens_details") or payload.get("input_tokens_details"))
    completion_details = _mapping(
        payload.get("completion_tokens_details") or payload.get("output_tokens_details")
    )
    input_tokens = _optional_token(payload, "inputTokens", "input_tokens", "prompt_tokens", "promptTokens")
    output_tokens = _optional_token(
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
    total_tokens = (
        provider_total
        if provider_total is not None
        else int(input_tokens or 0) + int(output_tokens or 0)
    )
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


def _price_decimal(payload: Mapping[str, Any], key: str) -> Decimal:
    value = _optional_price_decimal(payload, key)
    if value is None:
        raise ValueError(f"model price requires {key}")
    return value


def _optional_price_decimal(payload: Mapping[str, Any], key: str) -> Decimal | None:
    if key not in payload or payload[key] is None:
        return None
    try:
        value = Decimal(str(payload[key]))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("model prices must be decimal values") from exc
    if not value.is_finite() or value < 0:
        raise ValueError("model prices must be finite and non-negative")
    if value > Decimal("9999999999.9999999999"):
        raise ValueError("model price exceeds fixed-decimal limits")
    return value


def _cost_decimal(value: Decimal) -> Decimal:
    if not value.is_finite() or value < 0 or value > Decimal("9999999999.9999999999"):
        raise ValueError("model cost exceeds fixed-decimal limits")
    try:
        return value.quantize(Decimal("0.0000000001"))
    except InvalidOperation as exc:
        raise ValueError("model cost cannot be represented at fixed precision") from exc
