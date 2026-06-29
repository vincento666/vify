"""Spec 213.3.4 contract — dispatch-irrelevant banned fields are not persisted on checkpoint writes.

Repository.create_checkpoint MUST ignore explicit ``pending_prompt`` writes
(logging a warning) so the SOP Router stops mirroring chatflow runtime state.
``scoped_variables`` is filtered to retain only the ``__chatflow`` JSON key,
keeping chatflow trace projections workable.

``current_step`` / ``collected`` / ``business_refs`` writes are preserved
(carved out of 213.3.4 because router / policy / SOP-adapter / aggregator
read consumers still depend on them) and are scheduled for removal in slice
213.3.5.
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

    def test_create_checkpoint_writes_empty_placeholder_for_pending_prompt(self) -> None:
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
            )

            # pending_prompt writes must be coerced to the empty placeholder.
            self.assertEqual(checkpoint["pending_prompt"], "")
            # current_step writes are still permitted in 213.3.4 (carved out).
            self.assertEqual(checkpoint["current_step"], "collect_order_no")

    def test_create_task_still_writes_business_refs(self) -> None:
        # business_refs is the carved-out exception for 213.3.4 — verify it
        # is still persisted as before (removal deferred to 213.3.5).
        with _session() as session:
            repository = RuntimeLabRepository(session)
            runtime_session = repository.create_session()

            task = repository.create_task(
                int(runtime_session["id"]),
                sop_id="refund_ticket",
                business_refs={"order_no": "T1"},
            )

            self.assertEqual(task["business_refs"], {"order_no": "T1"})


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session("runtime_lab_banned_writes", register=register_runtime_lab_tables) as session:
        yield session


if __name__ == "__main__":
    unittest.main()
