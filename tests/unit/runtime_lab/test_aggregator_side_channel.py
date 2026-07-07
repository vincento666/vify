"""Spec 213.3.5a — RuntimeLabBusinessContextAggregator in-memory side-channel.

After spec 213.3.5e bans business_refs writes, the aggregator's DB fallback
fails. Add an in-memory side-channel (per-session dict) populated by the
service after each adapter turn so context survives without DB writes.

This sub-slice adds the side-channel WITHOUT removing the DB fallback;
later sub-slices ban writes and remove the fallback.
"""

import unittest
from unittest.mock import MagicMock

from app.core.errors import BizError, ErrorCode
from app.modules.runtime_lab.domain.aggregator import (
    RuntimeLabBusinessContextAggregator,
)


class AggregatorSideChannelTest(unittest.TestCase):
    def _empty_repository(self) -> MagicMock:
        repository = MagicMock()
        repository.list_tasks.return_value = []
        repository.get_active_task.return_value = None
        return repository

    def test_record_turn_context_stores_per_session_overlay(self) -> None:
        repository = self._empty_repository()
        workflow_service = MagicMock()
        agg = RuntimeLabBusinessContextAggregator(repository, workflow_service)

        agg.record_turn_context(session_id=1, context={"order_no": "T123"})

        self.assertEqual(agg.collect(session_id=1), {"order_no": "T123"})

    def test_record_turn_context_isolates_sessions(self) -> None:
        repository = self._empty_repository()
        workflow_service = MagicMock()
        agg = RuntimeLabBusinessContextAggregator(repository, workflow_service)

        agg.record_turn_context(session_id=1, context={"order_no": "S1"})
        agg.record_turn_context(session_id=2, context={"order_no": "S2"})

        self.assertEqual(agg.collect(session_id=1), {"order_no": "S1"})
        self.assertEqual(agg.collect(session_id=2), {"order_no": "S2"})

    def test_record_turn_context_overrides_previous_turn_keys(self) -> None:
        repository = self._empty_repository()
        workflow_service = MagicMock()
        agg = RuntimeLabBusinessContextAggregator(repository, workflow_service)

        agg.record_turn_context(session_id=1, context={"order_no": "FIRST", "phone": "111"})
        agg.record_turn_context(session_id=1, context={"order_no": "SECOND"})

        self.assertEqual(
            agg.collect(session_id=1),
            {"order_no": "SECOND", "phone": "111"},
        )

    def test_collect_prefers_chatflow_over_overlay_without_business_refs_fallback(self) -> None:
        repository = MagicMock()
        repository.list_tasks.return_value = [
            {
                "id": 11,
                "session_id": 1,
                "status": "COMPLETED",
                "business_refs": {"order_no": "DB", "phone": "PHONE_DB"},
                "chatflow_id": 42,
                "chatflow_session_id": 9001,
            }
        ]
        repository.get_active_task.return_value = None
        workflow_service = MagicMock()
        workflow_service.get_session_state.return_value = {
            "variables": {"conversation": {"order_no": "CHATFLOW"}}
        }
        agg = RuntimeLabBusinessContextAggregator(repository, workflow_service)

        agg.record_turn_context(
            session_id=1,
            context={"order_no": "OVERLAY", "extra": "OVERLAY_ONLY"},
        )

        result = agg.collect(session_id=1)

        # chatflow wins for order_no
        self.assertEqual(result["order_no"], "CHATFLOW")
        # business_refs is no longer a fallback after schema drop.
        self.assertNotIn("phone", result)
        # overlay-only key survives
        self.assertEqual(result["extra"], "OVERLAY_ONLY")

    def test_collect_falls_back_to_overlay_when_chatflow_bizerror(self) -> None:
        repository = MagicMock()
        repository.list_tasks.return_value = [
            {
                "id": 11,
                "session_id": 1,
                "status": "COMPLETED",
                "business_refs": {},
                "chatflow_id": 42,
                "chatflow_session_id": 9001,
            }
        ]
        repository.get_active_task.return_value = None
        workflow_service = MagicMock()
        workflow_service.get_session_state.side_effect = BizError(
            ErrorCode.NOT_FOUND, "Chatflow session not found"
        )
        agg = RuntimeLabBusinessContextAggregator(repository, workflow_service)

        agg.record_turn_context(session_id=1, context={"order_no": "FROM_OVERLAY"})

        self.assertEqual(agg.collect(session_id=1), {"order_no": "FROM_OVERLAY"})


if __name__ == "__main__":
    unittest.main()
