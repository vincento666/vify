import json
import unittest
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from app.core.schema import register_baseline_tables
from app.modules.workflow.domain.runtime_v2 import ChatflowRuntimeV2Service
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.realtime.redis_streams import (
    InMemoryRuntimeEventStreamBus,
    RedisRuntimeEventStreamBus,
)
from app.modules.workflow.infra.repository import WorkflowRepository
from app.modules.workflow.web.router import _iter_runtime_v2_sse, runtime_v2_stream_events
from tests.support.mysql import mysql8_session


class RuntimeV2RedisStreamsTest(unittest.TestCase):
    def test_append_event_publishes_committed_event_to_stream_bus(self) -> None:
        bus = InMemoryRuntimeEventStreamBus()
        with _session() as session:
            repository = ChatflowStateRepository(session, event_stream_bus=bus)

            event = repository.append_event(
                session_id="chatflow-v2-redis",
                chatflow_id=10,
                run_id=20,
                event_type="workflow_run_started",
                payload={"message": "stream me"},
            )

        streamed = bus.read_after(run_id=20, after_sequence=0, count=10, block_ms=0)
        self.assertEqual(len(streamed), 1)
        self.assertEqual(streamed[0]["sequence"], event["sequence"])
        self.assertEqual(streamed[0]["type"], "workflow_run_started")
        self.assertEqual(streamed[0]["source"], "chatflow_runtime_v2")
        self.assertEqual(
            streamed[0]["payload"],
            {"message": "stream me", "ownerType": "CHATFLOW", "source": "chatflow_runtime_v2"},
        )

    def test_runtime_v2_sse_reads_stream_bus_before_db_polling(self) -> None:
        bus = InMemoryRuntimeEventStreamBus()
        bus.publish(
            {
                "runId": 44,
                "sequence": 2,
                "type": "workflow_node_started",
                "level": "L1",
                "source": "chatflow_runtime_v2",
                "payload": {"nodeKey": "message_1"},
            }
        )

        emitted = next(
            _iter_runtime_v2_sse(
                _FailingDbPollingService(),
                run_id=44,
                after_sequence=1,
                heartbeat_ms=100,
                test_limit=1,
                test_heartbeat_limit=None,
                event_stream_bus=bus,
            )
        )

        self.assertEqual(json.loads(emitted.removeprefix("data: ").strip())["sequence"], 2)

    def test_runtime_v2_sse_falls_back_to_db_when_stream_has_no_event(self) -> None:
        emitted = next(
            _iter_runtime_v2_sse(
                _DbPollingService(),
                run_id=45,
                after_sequence=1,
                heartbeat_ms=100,
                test_limit=1,
                test_heartbeat_limit=None,
                event_stream_bus=InMemoryRuntimeEventStreamBus(),
            )
        )

        event = json.loads(emitted.removeprefix("data: ").strip())
        self.assertEqual(event["sequence"], 2)
        self.assertEqual(event["type"], "workflow_run_completed")

    def test_redis_stream_reader_normalizes_out_of_order_and_duplicate_xadds_by_sequence(self) -> None:
        bus = RedisRuntimeEventStreamBus(_FakeRedis())
        bus.publish(_stream_event(run_id=46, sequence=2, event_type="workflow_run_completed"))
        bus.publish(_stream_event(run_id=46, sequence=1, event_type="llm_delta"))
        bus.publish(_stream_event(run_id=46, sequence=1, event_type="llm_delta"))

        events = bus.read_after(run_id=46, after_sequence=0, count=10, block_ms=0)
        first_page = bus.read_after(run_id=46, after_sequence=0, count=1, block_ms=0)

        self.assertEqual([event["sequence"] for event in events], [1, 2])
        self.assertEqual([event["type"] for event in events], ["llm_delta", "workflow_run_completed"])
        self.assertEqual([event["sequence"] for event in first_page], [1])

    def test_fresh_event_reader_escapes_an_existing_sse_session_snapshot(self) -> None:
        with _session() as session:
            run_id = WorkflowRepository(session).create_run(47, {"sys.query": "fresh stream backlog"})
            state_repository = ChatflowStateRepository(session)
            state_repository.append_event(
                session_id="chatflow-v2-fresh-events",
                chatflow_id=47,
                run_id=run_id,
                event_type="workflow_node_started",
            )
            service = ChatflowRuntimeV2Service(WorkflowRepository(session), state_repository)
            self.assertEqual([event["sequence"] for event in service.list_events(run_id)["list"]], [1])

            factory = sessionmaker(bind=session.get_bind(), autoflush=False, autocommit=False, expire_on_commit=False)
            with factory() as writer_session:
                ChatflowStateRepository(writer_session).append_event(
                    session_id="chatflow-v2-fresh-events",
                    chatflow_id=47,
                    run_id=run_id,
                    event_type="workflow_run_completed",
                )

            stale = service.list_events(run_id)["list"]
            fresh = service.list_events_fresh(run_id)["list"]
            late_only_bus = InMemoryRuntimeEventStreamBus()
            late_only_bus.publish(_stream_event(run_id=run_id, sequence=2, event_type="workflow_run_completed"))
            recovered = runtime_v2_stream_events(
                service,
                event_stream_bus=late_only_bus,
                run_id=run_id,
                after_sequence=0,
                heartbeat_ms=100,
                count=10,
            )

        self.assertEqual([event["sequence"] for event in stale], [1])
        self.assertEqual([event["sequence"] for event in fresh], [1, 2])
        self.assertEqual([event["sequence"] for event in recovered], [1, 2])


class _FailingDbPollingService:
    def list_events(self, *_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("DB polling should not run when Redis stream has newer events")


class _DbPollingService:
    def list_events(self, *_args: object, **_kwargs: object) -> dict[str, object]:
        return {
            "list": [
                {
                    "runId": 45,
                    "sequence": 2,
                    "type": "workflow_run_completed",
                    "payload": {"final": "done"},
                }
            ]
        }


class _FakeRedis:
    def __init__(self) -> None:
        self._streams: dict[str, list[tuple[str, dict[str, str]]]] = {}

    def xadd(
        self,
        key: str,
        fields: dict[str, str],
        *,
        maxlen: int,
        approximate: bool,
    ) -> str:
        del maxlen, approximate
        rows = self._streams.setdefault(key, [])
        entry_id = f"{len(rows) + 1}-0"
        rows.append((entry_id, dict(fields)))
        return entry_id

    def xrange(self, key: str, *, min: str, max: str) -> list[tuple[str, dict[str, str]]]:
        del min, max
        return list(self._streams.get(key, []))


def _stream_event(*, run_id: int, sequence: int, event_type: str) -> dict[str, object]:
    return {
        "id": sequence,
        "runId": run_id,
        "sequence": sequence,
        "type": event_type,
        "payload": {"ownerType": "CHATFLOW"},
    }


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session("runtime_v2_redis_streams", register=register_baseline_tables) as session:
        yield session


if __name__ == "__main__":
    unittest.main()
