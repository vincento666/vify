from __future__ import annotations

import json
import threading
import time
from collections.abc import Mapping
from datetime import date, datetime
from typing import Any, Protocol


class RuntimeEventStreamBus(Protocol):
    def publish(self, event: Mapping[str, Any]) -> None:
        ...

    def read_after(
        self,
        *,
        run_id: int,
        after_sequence: int,
        count: int = 100,
        block_ms: int = 0,
    ) -> list[dict[str, Any]]:
        ...


class InMemoryRuntimeEventStreamBus:
    def __init__(self) -> None:
        self._events_by_run: dict[int, list[dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def publish(self, event: Mapping[str, Any]) -> None:
        normalized = normalize_runtime_stream_event(event)
        run_id = int(normalized["runId"])
        with self._lock:
            events = self._events_by_run.setdefault(run_id, [])
            if not any(int(existing["sequence"]) == int(normalized["sequence"]) for existing in events):
                events.append(normalized)
                events.sort(key=lambda row: int(row["sequence"]))

    def read_after(
        self,
        *,
        run_id: int,
        after_sequence: int,
        count: int = 100,
        block_ms: int = 0,
    ) -> list[dict[str, Any]]:
        deadline = time.monotonic() + (block_ms / 1000)
        while True:
            with self._lock:
                events = [
                    dict(event)
                    for event in self._events_by_run.get(int(run_id), [])
                    if int(event["sequence"]) > int(after_sequence)
                ]
            if events or block_ms <= 0 or time.monotonic() >= deadline:
                return events[:count]
            time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))


class RedisRuntimeEventStreamBus:
    def __init__(self, redis_client: Any, *, stream_prefix: str = "hify:runtime-v2:events") -> None:
        self._redis = redis_client
        self._stream_prefix = stream_prefix.rstrip(":")

    @classmethod
    def from_url(cls, redis_url: str) -> "RedisRuntimeEventStreamBus":
        import redis

        return cls(redis.Redis.from_url(redis_url, decode_responses=True))

    def publish(self, event: Mapping[str, Any]) -> None:
        normalized = normalize_runtime_stream_event(event)
        self._redis.xadd(
            self._stream_key(int(normalized["runId"])),
            {"event": json.dumps(normalized, ensure_ascii=False, default=_json_default)},
            maxlen=10_000,
            approximate=True,
        )

    def read_after(
        self,
        *,
        run_id: int,
        after_sequence: int,
        count: int = 100,
        block_ms: int = 0,
    ) -> list[dict[str, Any]]:
        if block_ms > 0:
            deadline = time.monotonic() + (block_ms / 1000)
            while time.monotonic() < deadline:
                events = self._read_available(run_id=run_id, after_sequence=after_sequence, count=count)
                if events:
                    return events
                time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
        return self._read_available(run_id=run_id, after_sequence=after_sequence, count=count)

    def _read_available(self, *, run_id: int, after_sequence: int, count: int) -> list[dict[str, Any]]:
        rows = self._redis.xrange(self._stream_key(run_id), min="-", max="+")
        events: list[dict[str, Any]] = []
        for _entry_id, fields in rows:
            raw_event = fields.get("event") if isinstance(fields, dict) else None
            if not raw_event:
                continue
            event = json.loads(raw_event)
            if int(event.get("sequence") or 0) > int(after_sequence):
                events.append(event)
            if len(events) >= count:
                break
        return events

    def _stream_key(self, run_id: int) -> str:
        return f"{self._stream_prefix}:{int(run_id)}"


def normalize_runtime_stream_event(event: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(event.get("payload") or {})
    sequence = int(event.get("sequence") or 0)
    run_id = int(event.get("runId") or event.get("run_id") or 0)
    event_id = int(event.get("id") or sequence)
    event_type = str(event.get("type") or event.get("event_type") or "")
    created_at = event.get("createdAt") or event.get("created_at") or datetime.now()
    return {
        "id": event_id,
        "runId": run_id,
        "sequence": sequence,
        "type": event_type,
        "level": str(event.get("level") or payload.get("level") or "L1"),
        "source": str(event.get("source") or payload.get("source") or "runtime_v2"),
        "actor": str(event.get("actor") or payload.get("actor") or "system"),
        "nodeId": str(event.get("nodeId") or event.get("node_key") or ""),
        "checkpointId": event.get("checkpointId") or event.get("checkpoint_id"),
        "spanId": event.get("spanId") or payload.get("spanId"),
        "parentSpanId": event.get("parentSpanId") or payload.get("parentSpanId"),
        "payload": payload,
        "createdAt": _format_datetime(created_at),
    }


def _format_datetime(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _json_default(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)
