"""Spec 213.3.5g contract — banned runtime_lab write targets are gone.

Repository.create_task / update_task_state MUST ignore explicit
``current_step`` and ``business_refs`` kwargs for call-site compatibility, but
the row shape must not expose those mirror columns after schema drop.
"""

from contextlib import contextmanager
import unittest
from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables
from tests.support.mysql import mysql8_session


class BannedWriteIgnoredTest(unittest.TestCase):
    def test_checkpoint_repository_accessors_are_removed(self) -> None:
        self.assertFalse(hasattr(RuntimeLabRepository, "create_checkpoint"))
        self.assertFalse(hasattr(RuntimeLabRepository, "get_checkpoint"))
        self.assertFalse(hasattr(RuntimeLabRepository, "get_latest_checkpoint"))

    def test_create_task_ignores_current_step_and_business_refs(self) -> None:
        with _session() as session:
            repository = RuntimeLabRepository(session)
            runtime_session = repository.create_session()

            task = repository.create_task(
                int(runtime_session["id"]),
                sop_id="refund_ticket",
                current_step="explicit_step",
                business_refs={"order_no": "T1"},
            )

            self.assertNotIn("current_step", task)
            self.assertNotIn("business_refs", task)

    def test_update_task_state_ignores_current_step_and_business_refs(self) -> None:
        with _session() as session:
            repository = RuntimeLabRepository(session)
            runtime_session = repository.create_session()
            task = repository.create_task(
                int(runtime_session["id"]),
                sop_id="refund_ticket",
                status="PENDING",
            )

            updated = repository.update_task_state(
                int(task["id"]),
                status="RUNNING",
                current_step="explicit_step",
                business_refs={"order_no": "T1"},
            )

            self.assertNotIn("current_step", updated)
            self.assertNotIn("business_refs", updated)


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session("runtime_lab_banned_writes", register=register_runtime_lab_tables) as session:
        yield session


if __name__ == "__main__":
    unittest.main()
