from __future__ import annotations

import time
from typing import Any

from app.modules.workflow.web.router import _runtime_v2_stream_events


def test_reconnect_returns_db_backlog_without_waiting_on_empty_stream_bus() -> None:
    service = _DbBacklogService()
    bus = _BlockingEmptyBus()

    started_at = time.monotonic()
    events = _runtime_v2_stream_events(
        service,
        event_stream_bus=bus,
        run_id=219101,
        after_sequence=3,
        heartbeat_ms=500,
        count=100,
    )
    elapsed = time.monotonic() - started_at

    assert elapsed < 0.1
    assert bus.block_ms_values == [0]
    assert [event["sequence"] for event in events] == [4, 5]


def test_reconnect_uses_stream_bus_when_db_has_no_backlog() -> None:
    service = _EmptyDbService()
    bus = _LiveBus()

    events = _runtime_v2_stream_events(
        service,
        event_stream_bus=bus,
        run_id=219102,
        after_sequence=5,
        heartbeat_ms=500,
        count=100,
    )

    assert bus.block_ms_values == [0, 500]
    assert events == [
        {
            "runId": 219102,
            "sequence": 6,
            "type": "workflow_node_started",
            "payload": {"nodeKey": "message_1"},
        }
    ]


def test_realtime_gap_reads_fresh_durable_backlog_before_later_live_event() -> None:
    service = _FreshGapBacklogService()
    bus = _LaterLiveBus()

    events = _runtime_v2_stream_events(
        service,
        event_stream_bus=bus,
        run_id=219103,
        after_sequence=0,
        heartbeat_ms=500,
        count=100,
    )

    assert [event["sequence"] for event in events] == [1, 2]
    assert service.fresh_calls == [(219103, 0)]
    assert bus.block_ms_values == [0]


def test_realtime_internal_gap_reads_fresh_durable_backlog_before_later_live_event() -> None:
    service = _InternalGapBacklogService()
    bus = _InternalGapLiveBus()

    events = _runtime_v2_stream_events(
        service,
        event_stream_bus=bus,
        run_id=219104,
        after_sequence=0,
        heartbeat_ms=500,
        count=100,
    )

    assert [event["sequence"] for event in events] == [1, 2, 3]
    assert service.fresh_calls == [(219104, 0)]
    assert bus.block_ms_values == [0]


def test_realtime_gap_without_retained_predecessor_does_not_block_forever() -> None:
    service = _CompactedGapBacklogService()
    bus = _CompactedGapLiveBus()

    events = _runtime_v2_stream_events(
        service,
        event_stream_bus=bus,
        run_id=219105,
        after_sequence=0,
        heartbeat_ms=500,
        count=100,
    )

    assert [event["sequence"] for event in events] == [2]
    assert service.fresh_calls == [(219105, 0)]
    assert bus.block_ms_values == [0]


class _DbBacklogService:
    def list_events(self, run_id: int, after_sequence: int = 0) -> dict[str, Any]:
        assert run_id == 219101
        assert after_sequence == 3
        return {
            "list": [
                {"runId": run_id, "sequence": 4, "type": "workflow_node_started", "payload": {}},
                {"runId": run_id, "sequence": 5, "type": "workflow_run_completed", "payload": {}},
            ]
        }


class _EmptyDbService:
    def list_events(self, run_id: int, after_sequence: int = 0) -> dict[str, Any]:
        assert run_id == 219102
        assert after_sequence in {5, 6}
        return {"list": []}


class _FreshGapBacklogService:
    def __init__(self) -> None:
        self.fresh_calls: list[tuple[int, int]] = []

    def list_events(self, *_args: object, **_kwargs: object) -> dict[str, Any]:
        raise AssertionError("a Redis sequence gap must use the fresh durable backlog seam")

    def list_events_fresh(self, run_id: int, after_sequence: int = 0) -> dict[str, Any]:
        self.fresh_calls.append((run_id, after_sequence))
        return {
            "list": [
                {"runId": run_id, "sequence": 1, "type": "llm_delta", "payload": {"content": "a"}},
                {"runId": run_id, "sequence": 2, "type": "workflow_run_completed", "payload": {}},
            ]
        }


class _InternalGapBacklogService(_FreshGapBacklogService):
    def list_events_fresh(self, run_id: int, after_sequence: int = 0) -> dict[str, Any]:
        self.fresh_calls.append((run_id, after_sequence))
        return {
            "list": [
                {"runId": run_id, "sequence": 1, "type": "llm_delta", "payload": {"content": "a"}},
                {"runId": run_id, "sequence": 2, "type": "llm_delta", "payload": {"content": "b"}},
                {"runId": run_id, "sequence": 3, "type": "workflow_run_completed", "payload": {}},
            ]
        }


class _CompactedGapBacklogService(_FreshGapBacklogService):
    def list_events_fresh(self, run_id: int, after_sequence: int = 0) -> dict[str, Any]:
        self.fresh_calls.append((run_id, after_sequence))
        return {"list": []}


class _BlockingEmptyBus:
    def __init__(self) -> None:
        self.block_ms_values: list[int] = []

    def read_after(
        self,
        *,
        run_id: int,
        after_sequence: int,
        count: int = 100,
        block_ms: int = 0,
    ) -> list[dict[str, Any]]:
        self.block_ms_values.append(block_ms)
        time.sleep(block_ms / 1000)
        return []


class _LiveBus:
    def __init__(self) -> None:
        self.block_ms_values: list[int] = []

    def read_after(
        self,
        *,
        run_id: int,
        after_sequence: int,
        count: int = 100,
        block_ms: int = 0,
    ) -> list[dict[str, Any]]:
        self.block_ms_values.append(block_ms)
        assert run_id == 219102
        assert after_sequence == 5
        if block_ms == 0:
            return []
        return [
            {
                "runId": run_id,
                "sequence": 6,
                "type": "workflow_node_started",
                "payload": {"nodeKey": "message_1"},
            }
        ]


class _LaterLiveBus:
    def __init__(self) -> None:
        self.block_ms_values: list[int] = []

    def read_after(
        self,
        *,
        run_id: int,
        after_sequence: int,
        count: int = 100,
        block_ms: int = 0,
    ) -> list[dict[str, Any]]:
        del count
        self.block_ms_values.append(block_ms)
        assert run_id == 219103
        assert after_sequence == 0
        return [
            {
                "runId": run_id,
                "sequence": 2,
                "type": "workflow_run_completed",
                "payload": {},
            }
        ]


class _InternalGapLiveBus(_LaterLiveBus):
    def read_after(
        self,
        *,
        run_id: int,
        after_sequence: int,
        count: int = 100,
        block_ms: int = 0,
    ) -> list[dict[str, Any]]:
        del count
        self.block_ms_values.append(block_ms)
        assert run_id == 219104
        assert after_sequence == 0
        return [
            {"runId": run_id, "sequence": 1, "type": "llm_delta", "payload": {"content": "a"}},
            {"runId": run_id, "sequence": 3, "type": "workflow_run_completed", "payload": {}},
        ]


class _CompactedGapLiveBus(_LaterLiveBus):
    def read_after(
        self,
        *,
        run_id: int,
        after_sequence: int,
        count: int = 100,
        block_ms: int = 0,
    ) -> list[dict[str, Any]]:
        del count
        self.block_ms_values.append(block_ms)
        assert run_id == 219105
        assert after_sequence == 0
        return [{"runId": run_id, "sequence": 2, "type": "workflow_run_completed", "payload": {}}]
