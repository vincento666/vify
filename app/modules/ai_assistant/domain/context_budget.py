from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from typing import Any

from app.modules.ai_assistant.domain.memory_context import estimate_tokens


DEFAULT_CONTEXT_WINDOW_TOKENS = 128_000
WARNING_THRESHOLD = 70
CRITICAL_THRESHOLD = 90
PROTECTED_LAYERS = {"base", "AGENTS.md", "session_summary", "working_memory", "user_message"}


def estimate_context_budget(
    layers: list[dict[str, Any]],
    *,
    max_context_tokens: int = DEFAULT_CONTEXT_WINDOW_TOKENS,
) -> dict[str, Any]:
    max_tokens = max(1, int(max_context_tokens or DEFAULT_CONTEXT_WINDOW_TOKENS))
    normalized = [_normalize_layer(layer) for layer in layers]
    raw_tokens = sum(layer["tokens"] for layer in normalized)
    selected, dropped = _select_layers(normalized, max_tokens)
    selected_tokens = sum(layer["tokens"] for layer in selected)
    usage_percent = round((selected_tokens / max_tokens) * 100, 1)
    raw_usage_percent = round((raw_tokens / max_tokens) * 100, 1)
    warning_level = (
        "critical" if raw_usage_percent >= CRITICAL_THRESHOLD else "warning" if raw_usage_percent >= WARNING_THRESHOLD else "ok"
    )
    selected = [_with_share(layer, selected_tokens) for layer in selected]
    dropped = [_with_share(layer, raw_tokens) for layer in dropped]
    return {
        "usage": {
            "usedTokens": selected_tokens,
            "maxTokens": max_tokens,
            "usagePercent": usage_percent,
            "warningLevel": warning_level,
            "rawTokens": raw_tokens,
            "rawUsagePercent": raw_usage_percent,
        },
        "layers": [_with_share(layer, raw_tokens) for layer in normalized],
        "selectedLayers": selected,
        "droppedLayers": dropped,
        "dropReasons": [
            {
                "name": layer["name"],
                "reason": "context_window_budget",
                "tokens": layer["tokens"],
            }
            for layer in dropped
        ],
        "estimatedAt": datetime.now().isoformat(),
    }


def build_compaction_snapshot(
    *,
    raw_content: str,
    summary: str,
    source_message_ids: list[int],
    source_event_ids: list[int],
    algorithm: str,
) -> dict[str, Any]:
    raw_tokens = estimate_tokens(raw_content)
    summary_tokens = estimate_tokens(summary)
    saved_percent = 0.0
    if raw_tokens:
        saved_percent = round(max(0, raw_tokens - summary_tokens) / raw_tokens * 100, 1)
    return {
        "rawTokens": raw_tokens,
        "summaryTokens": summary_tokens,
        "savedPercent": saved_percent,
        "sourceMessageIds": [int(item) for item in source_message_ids],
        "sourceEventIds": [int(item) for item in source_event_ids],
        "algorithm": algorithm,
        "summaryHash": sha256(summary.encode("utf-8")).hexdigest(),
        "createdAt": datetime.now().isoformat(),
    }


def context_window_from_context(context: dict[str, Any] | None) -> int:
    raw = (context or {}).get("aiAssistantContextBudget")
    if isinstance(raw, dict):
        value = raw.get("maxContextTokens")
        if isinstance(value, int | float) and value > 0:
            return int(value)
        if isinstance(value, str) and value.strip().isdigit():
            return int(value)
    return DEFAULT_CONTEXT_WINDOW_TOKENS


def _normalize_layer(layer: dict[str, Any]) -> dict[str, Any]:
    content = str(layer.get("content") or "")
    tokens = layer.get("tokens")
    if not isinstance(tokens, int | float):
        tokens = estimate_tokens(content)
    return {
        "name": str(layer.get("name") or "unknown"),
        "tokens": max(0, int(tokens)),
        "source": layer.get("source"),
        "hash": layer.get("hash"),
        "selected": True,
    }


def _select_layers(layers: list[dict[str, Any]], max_tokens: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected = [dict(layer) for layer in layers]
    dropped: list[dict[str, Any]] = []
    while sum(layer["tokens"] for layer in selected) > max_tokens:
        candidate_index = _largest_droppable_index(selected)
        if candidate_index is None:
            break
        dropped_layer = selected.pop(candidate_index)
        dropped_layer["selected"] = False
        dropped.append(dropped_layer)
    return selected, dropped


def _largest_droppable_index(layers: list[dict[str, Any]]) -> int | None:
    candidates = [
        (index, layer)
        for index, layer in enumerate(layers)
        if layer["name"] not in PROTECTED_LAYERS
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[1]["tokens"])[0]


def _with_share(layer: dict[str, Any], total_tokens: int) -> dict[str, Any]:
    copied = dict(layer)
    copied["sharePercent"] = round((copied["tokens"] / total_tokens) * 100, 1) if total_tokens else 0.0
    return copied
