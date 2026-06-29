"""Spec 213.3.5e-prep — current_step in-memory side-channel.

Prepares for banning ``runtime_lab_checkpoint.current_step`` writes by pinning
an in-memory task-step overlay on the runtime-lab aggregator. The overlay must
be refreshed after adapter turns and must take precedence over stale checkpoint
rows when policy decides whether an active SOP can be interrupted.
"""

from contextlib import contextmanager
import unittest
from collections.abc import Iterator
from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from app.modules.runtime_lab.domain.aggregator import RuntimeLabBusinessContextAggregator
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables
from tests.support.mysql import mysql8_session


class CurrentStepSideChannelTest(unittest.TestCase):
    def test_aggregator_records_task_current_step_by_task_id(self) -> None:
        aggregator = RuntimeLabBusinessContextAggregator(MagicMock(), MagicMock())

        self.assertIsNone(aggregator.task_current_step(10))

        aggregator.record_task_step(10, "collect_order_no")
        aggregator.record_task_step(10, "confirm")

        self.assertEqual(aggregator.task_current_step(10), "confirm")

    def test_service_records_current_step_after_continue_turn(self) -> None:
        with _session() as session:
            repository = RuntimeLabRepository(session)
            service = RuntimeLabService(repository)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            service.handle_message(session_id, "我要退票")
            active_task = repository.get_active_task(session_id)
            assert active_task is not None
            task_id = int(active_task["id"])

            service.handle_message(session_id, "TK-100")

            self.assertEqual(service._aggregator.task_current_step(task_id), "confirm")

    def test_classifier_decision_uses_current_step_overlay_before_checkpoint_row(self) -> None:
        with _session() as session:
            repository = RuntimeLabRepository(session)
            service = RuntimeLabService(repository)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            service.handle_message(session_id, "我要退票")
            service.handle_message(session_id, "TK-100")
            active_task = repository.get_active_task(session_id)
            assert active_task is not None
            task_id = int(active_task["id"])

            latest_checkpoint = repository.get_latest_checkpoint(task_id)
            assert latest_checkpoint is not None
            stale_checkpoint = dict(latest_checkpoint)
            stale_checkpoint["current_step"] = "collect_order_no"
            service._repository.get_latest_checkpoint = MagicMock(return_value=stale_checkpoint)  # type: ignore[method-assign]
            service._aggregator.record_task_step(task_id, "confirm")

            overlaid = service._latest_checkpoint_with_overlay_step(active_task)

            self.assertIsNotNone(overlaid)
            assert overlaid is not None
            self.assertEqual(overlaid["current_step"], "confirm")

            rejected = service.handle_message(session_id, "我要改签")

            self.assertEqual(rejected.route_decision.action, "REJECT_SWITCH_CONTINUE_ACTIVE")
            self.assertEqual(rejected.active_task["sop_id"], "refund_ticket")


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session(
        "runtime_lab_current_step_side_channel", register=register_runtime_lab_tables
    ) as session:
        yield session


if __name__ == "__main__":
    unittest.main()
