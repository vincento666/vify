from __future__ import annotations

from typing import Any

from app.core.schema import register_baseline_tables
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.realtime.redis_streams import InMemoryRuntimeEventStreamBus
from tests.support.mysql import mysql8_session


def test_redis_failure_falls_back_to_db_event_recovery_and_outbox_replay() -> None:
    failing_bus = _FailingBus()
    replay_bus = InMemoryRuntimeEventStreamBus()
    chatflow_id = 2217
    run_id = 221_700_002

    with mysql8_session("runtime_chaos_redis_failure", register=register_baseline_tables) as session:
        repository = ChatflowStateRepository(session, event_stream_bus=failing_bus)
        event = repository.append_event(
            session_id="runtime-chaos-redis",
            chatflow_id=chatflow_id,
            run_id=run_id,
            event_type="workflow_node_completed",
            node_key="message_1",
            payload={"output": {"answer": "db-recovered"}},
        )
        db_events = repository.list_events(chatflow_id, run_id)
        pending = repository.list_event_outbox(run_id=run_id, statuses=("FAILED", "PENDING"))
        replay = repository.replay_event_outbox(run_id=run_id, event_stream_bus=replay_bus, limit=10)
        streamed = replay_bus.read_after(run_id=run_id, after_sequence=0, count=10, block_ms=0)
        remaining = repository.list_event_outbox(run_id=run_id, statuses=("FAILED", "PENDING"))

    assert [row["id"] for row in db_events] == [event["id"]]
    assert db_events[0]["sequence"] == 1
    assert pending[0]["status"] == "FAILED"
    assert "redis unavailable" in str(pending[0]["last_error"])
    assert replay == {"published": 1, "failed": 0}
    assert [row["id"] for row in streamed] == [event["id"]]
    assert remaining == []


class _FailingBus:
    def publish(self, event: dict[str, Any]) -> None:
        raise RuntimeError(f"redis unavailable for run {event['run_id']}")

    def read_after(
        self,
        *,
        run_id: int,
        after_sequence: int,
        count: int = 100,
        block_ms: int = 0,
    ) -> list[dict[str, Any]]:
        return []
