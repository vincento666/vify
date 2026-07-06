from __future__ import annotations

from datetime import datetime
from typing import Any


def text_delta_payload(
    *,
    index: int,
    delta: str,
    model: str,
    source: str,
    round_index: int | None = None,
    phase: str | None = None,
    streaming: bool = True,
    raw: bool = True,
    synthetic: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "index": index,
        "delta": delta,
        "chunk": delta,
        "model": model,
        "source": source,
        "streaming": streaming,
        "raw": raw,
    }
    if synthetic:
        payload["synthetic"] = True
    if round_index is not None:
        payload["roundIndex"] = round_index
    if phase:
        payload["phase"] = phase
    return payload


def stream_fallback_payload(*, model: str, source: str, reason: str = "provider_non_streaming") -> dict[str, Any]:
    return {
        "model": model,
        "source": source,
        "reason": reason,
        "streaming": False,
        "fallback": True,
    }


def heartbeat_payload(*, run_id: int, after_sequence: int) -> dict[str, Any]:
    return {
        "runId": run_id,
        "afterSequence": after_sequence,
        "heartbeatAt": datetime.now().isoformat(),
    }


def last_sequence(events: list[dict[str, Any]], fallback: int = 0) -> int:
    if not events:
        return fallback
    return max(int(event["sequence"]) for event in events)
