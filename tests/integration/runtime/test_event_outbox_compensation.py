from __future__ import annotations

from typing import Any

from app.core.schema import register_baseline_tables
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.realtime.redis_streams import InMemoryRuntimeEventStreamBus
from tests.support.mysql import mysql8_session


def test_event_publish_failure_records_outbox_and_replay_compensates_stream_bus() -> None:
    failing_bus = _FailingBus()
    replay_bus = InMemoryRuntimeEventStreamBus()

    with mysql8_session("runtime_event_outbox_compensation", register=register_baseline_tables) as session:
        repository = ChatflowStateRepository(session, event_stream_bus=failing_bus)
        event = repository.append_event(
            session_id="runtime-v2-outbox",
            chatflow_id=2191,
            run_id=219101,
            event_type="workflow_run_started",
            node_key="start",
            payload={"message": "must replay"},
        )

        pending = repository.list_event_outbox(run_id=219101, statuses=("FAILED", "PENDING"))
        assert len(pending) == 1
        assert pending[0]["event_id"] == event["id"]
        assert pending[0]["run_id"] == 219101
        assert pending[0]["status"] == "FAILED"
        assert pending[0]["attempt_count"] == 1
        assert "redis down" in str(pending[0]["last_error"])

        result = repository.replay_event_outbox(run_id=219101, event_stream_bus=replay_bus, limit=10)

        streamed = replay_bus.read_after(run_id=219101, after_sequence=0, count=10, block_ms=0)
        remaining = repository.list_event_outbox(run_id=219101, statuses=("FAILED", "PENDING"))

    assert result == {"published": 1, "failed": 0}
    assert [row["id"] for row in streamed] == [event["id"]]
    assert [row["sequence"] for row in streamed] == [event["sequence"]]
    assert remaining == []


class _FailingBus:
    def publish(self, event: dict[str, Any]) -> None:
        raise RuntimeError(f"redis down for run {event['run_id']}")

    def read_after(
        self,
        *,
        run_id: int,
        after_sequence: int,
        count: int = 100,
        block_ms: int = 0,
    ) -> list[dict[str, Any]]:
        return []
