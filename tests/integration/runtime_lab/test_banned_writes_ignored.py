"""Spec 213.3.5e contract — banned runtime_lab writes are ignored.

Repository.create_task / update_task_state MUST ignore explicit
``current_step`` and ``business_refs`` writes. ``business_refs`` is kept as an
empty placeholder until schema drop, while ``current_step`` keeps its existing
server default.

Repository.create_checkpoint MUST ignore explicit ``current_step``,
``pending_prompt``, and ``collected`` writes. It writes empty placeholders for
NOT NULL columns and filters ``scoped_variables`` to retain only the
``__chatflow`` JSON key.
"""

from contextlib import contextmanager
import unittest
from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables
from tests.support.mysql import mysql8_session


class BannedWriteIgnoredTest(unittest.TestCase):
    def test_create_checkpoint_filters_scoped_variables_to_chatflow_key(self) -> None:
        with _session() as session:
            repository = RuntimeLabRepository(session)
            runtime_session = repository.create_session()
            task = repository.create_task(
                int(runtime_session["id"]),
                sop_id="refund_ticket",
            )

            checkpoint = repository.create_checkpoint(
                int(runtime_session["id"]),
                int(task["id"]),
                sop_id="refund_ticket",
                current_step="collect_order_no",
                pending_prompt="",
                scoped_variables={
                    "conversation.foo": "bar",
                    "__chatflow": {"runId": 5, "sessionId": "abc"},
                },
            )

            # Only the __chatflow key survives.
            self.assertEqual(
                checkpoint["scoped_variables"],
                {"__chatflow": {"runId": 5, "sessionId": "abc"}},
            )

    def test_create_checkpoint_drops_scoped_variables_when_no_chatflow_key(self) -> None:
        with _session() as session:
            repository = RuntimeLabRepository(session)
            runtime_session = repository.create_session()
            task = repository.create_task(
                int(runtime_session["id"]),
                sop_id="refund_ticket",
            )

            checkpoint = repository.create_checkpoint(
                int(runtime_session["id"]),
                int(task["id"]),
                sop_id="refund_ticket",
                current_step="collect_order_no",
                pending_prompt="",
                scoped_variables={"conversation.foo": "bar"},
            )

            self.assertEqual(checkpoint["scoped_variables"], {})

    def test_create_checkpoint_writes_empty_placeholders_for_banned_fields(self) -> None:
        with _session() as session:
            repository = RuntimeLabRepository(session)
            runtime_session = repository.create_session()
            task = repository.create_task(
                int(runtime_session["id"]),
                sop_id="refund_ticket",
            )

            checkpoint = repository.create_checkpoint(
                int(runtime_session["id"]),
                int(task["id"]),
                sop_id="refund_ticket",
                current_step="collect_order_no",
                pending_prompt="explicit prompt",
                collected={"order_no": "T1"},
            )

            self.assertEqual(checkpoint["current_step"], "")
            self.assertEqual(checkpoint["pending_prompt"], "")
            self.assertEqual(checkpoint["collected"], {})

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

            self.assertEqual(task["current_step"], "collect_order_no")
            self.assertEqual(task["business_refs"], {})

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

            self.assertEqual(updated["current_step"], "collect_order_no")
            self.assertEqual(updated["business_refs"], {})


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session("runtime_lab_banned_writes", register=register_runtime_lab_tables) as session:
        yield session


if __name__ == "__main__":
    unittest.main()
