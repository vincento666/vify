"""Spec 216.3 — current_step is not mirrored in the RuntimeLab ledger."""

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
    def test_aggregator_no_longer_records_task_current_step_by_task_id(self) -> None:
        aggregator = RuntimeLabBusinessContextAggregator(MagicMock(), MagicMock())

        self.assertFalse(hasattr(aggregator, "task_current_step"))
        self.assertFalse(hasattr(aggregator, "record_task_step"))

    def test_service_resolves_current_step_from_adapter_child_checkpoint_after_continue_turn(self) -> None:
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

            resolved = service._latest_checkpoint_with_overlay_step(  # noqa: SLF001
                repository.get_task(task_id)
            )
            self.assertEqual(resolved, {"current_step": "confirm"})

    def test_classifier_decision_uses_child_runtime_before_stale_event_ledger(self) -> None:
        with _session() as session:
            repository = RuntimeLabRepository(session)
            service = RuntimeLabService(repository)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            service.handle_message(session_id, "我要退票")
            service.handle_message(session_id, "TK-100")
            active_task = repository.get_active_task(session_id)
            assert active_task is not None

            original_list_events = service._repository.list_events
            stale_events = [
                event
                if event["event_type"] != "TASK_CONTINUED"
                else {**event, "payload": {**event["payload"], "currentStep": "collect_order_no"}}
                for event in original_list_events(session_id)
            ]
            service._repository.list_events = MagicMock(return_value=stale_events)  # type: ignore[method-assign]

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
