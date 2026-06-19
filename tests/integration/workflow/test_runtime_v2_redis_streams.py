import json
import unittest
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.core.schema import register_baseline_tables
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.realtime.redis_streams import InMemoryRuntimeEventStreamBus
from app.modules.workflow.web.router import _iter_runtime_v2_sse
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
        self.assertEqual(streamed[0]["payload"], {"message": "stream me"})

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


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session("runtime_v2_redis_streams", register=register_baseline_tables) as session:
        yield session


if __name__ == "__main__":
    unittest.main()
