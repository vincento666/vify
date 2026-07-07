from contextlib import contextmanager
import unittest
from collections.abc import Iterator

from sqlalchemy.orm import Session

from tests.support.mysql import mysql8_session
from app.core.errors import BizError, ErrorCode
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables


class RuntimeLabKernelTest(unittest.TestCase):
    def test_command_replay_is_domain_level_and_preserves_invariants(self) -> None:
        with _session() as session:
            repository = RuntimeLabRepository(session)
            service = RuntimeLabService(repository)
            runtime_session = service.create_session()

            first = service.handle_command(int(runtime_session["id"]), "我要退票", idempotency_key="kernel-start")
            second = service.handle_command(int(runtime_session["id"]), "我要退票", idempotency_key="kernel-start")

            tasks = repository.list_tasks(int(runtime_session["id"]))
            events = repository.list_events(int(runtime_session["id"]))

            self.assertFalse(first.replayed)
            self.assertTrue(second.replayed)
            self.assertEqual(second.payload, first.payload)
            self.assertEqual([task["status"] for task in tasks], ["RUNNING"])
            self.assertTrue(all("current_step" not in task for task in tasks))
            self.assertEqual([event["sequence"] for event in events], list(range(1, len(events) + 1)))
            self.assertEqual(
                [event["event_type"] for event in events],
                ["SESSION_CREATED", "USER_MESSAGE", "ROUTE_DECISION", "TASK_STARTED"],
            )

            with self.assertRaises(BizError) as mismatch:
                service.handle_command(int(runtime_session["id"]), "我要改签", idempotency_key="kernel-start")
            self.assertEqual(mismatch.exception.code, ErrorCode.BAD_REQUEST)

    def test_missing_session_command_rejected_before_events(self) -> None:
        with _session() as session:
            repository = RuntimeLabRepository(session)
            service = RuntimeLabService(repository)

            with self.assertRaises(BizError) as missing:
                service.handle_command(404_404, "我要退票", idempotency_key="missing")

            self.assertEqual(missing.exception.code, ErrorCode.NOT_FOUND)
            self.assertEqual(repository.list_events(404_404), [])


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session("runtime_lab_kernel", register=register_runtime_lab_tables) as session:
        yield session
