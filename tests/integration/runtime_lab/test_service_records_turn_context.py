"""Spec 213.3.5a — RuntimeLabService records aggregator turn context after adapter turns.

Asserts that the service calls
:meth:`RuntimeLabBusinessContextAggregator.record_turn_context` with the
adapter result's ``collected`` after each adapter turn (start / continue /
suspend / resume) so the aggregator's in-memory side-channel is populated.

This is preparation for slice 213.3.5e (banning DB ``business_refs`` writes):
the side-channel becomes the primary post-chatflow context source.
"""

from contextlib import contextmanager
import unittest
from collections.abc import Iterator
from typing import Any

from sqlalchemy.orm import Session

from app.modules.runtime_lab.domain.aggregator import (
    RuntimeLabBusinessContextAggregator,
)
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables
from tests.support.mysql import mysql8_session


class _RecordingAggregator(RuntimeLabBusinessContextAggregator):
    def __init__(self, repository: RuntimeLabRepository) -> None:
        super().__init__(repository, None)
        self.recorded_calls: list[tuple[int, dict[str, Any]]] = []

    def record_turn_context(self, session_id: int, context: Any) -> None:  # type: ignore[override]
        self.recorded_calls.append((session_id, dict(context or {})))
        super().record_turn_context(session_id, context)


class ServiceRecordsTurnContextTest(unittest.TestCase):
    def test_handle_message_calls_aggregator_record_turn_context_on_each_adapter_turn(self) -> None:
        with _session() as session:
            repository = RuntimeLabRepository(session)
            aggregator = _RecordingAggregator(repository)
            service = RuntimeLabService(repository, aggregator=aggregator)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            # start_sop turn: "我要退票" triggers START_SOP refund_ticket
            service.handle_message(session_id, "我要退票")
            # suspend + start_sop turn: switch into invoice_apply suspends refund
            service.handle_message(session_id, "我要开发票")
            # continue_sop turn: provide invoice slot
            service.handle_message(session_id, "INV-200")
            # continue_sop turn: complete invoice
            service.handle_message(session_id, "确认")
            # resume_sop turn: pick up the suspended refund task
            service.handle_message(session_id, "继续刚才")

            self.assertGreaterEqual(
                len(aggregator.recorded_calls),
                5,
                f"Expected at least 5 record_turn_context calls, got {aggregator.recorded_calls!r}",
            )
            for recorded_session_id, _payload in aggregator.recorded_calls:
                self.assertEqual(recorded_session_id, session_id)

            # In-memory overlay must be populated for this session after the run
            overlay = aggregator._in_memory_overlay.get(session_id)
            self.assertIsNotNone(overlay)
            assert overlay is not None
            self.assertIsInstance(overlay, dict)


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session(
        "runtime_lab_service_records_turn_context", register=register_runtime_lab_tables
    ) as session:
        yield session


if __name__ == "__main__":
    unittest.main()
