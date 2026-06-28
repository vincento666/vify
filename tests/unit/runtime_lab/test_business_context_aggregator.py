"""Spec 213.3.3 — RuntimeLabBusinessContextAggregator scaffold tests.

Verifies the aggregator's behavior independent of service.py wire-up.
"""

import unittest
from unittest.mock import MagicMock

from app.core.errors import BizError, ErrorCode
from app.modules.runtime_lab.domain.aggregator import (
    RuntimeLabBusinessContextAggregator,
)


class AggregatorScaffoldTest(unittest.TestCase):
    def test_empty_session_returns_empty_context(self) -> None:
        repository = MagicMock()
        repository.list_tasks.return_value = []
        repository.get_active_task.return_value = None
        workflow_service = MagicMock()
        agg = RuntimeLabBusinessContextAggregator(repository, workflow_service)

        self.assertEqual(agg.collect(session_id=1), {})
        workflow_service.get_session_state.assert_not_called()

    def test_single_completed_task_with_chatflow_refs_returns_conversation(self) -> None:
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
        workflow_service.get_session_state.return_value = {
            "variables": {
                "conversation": {"order_no": "T123"},
            }
        }
        agg = RuntimeLabBusinessContextAggregator(repository, workflow_service)

        result = agg.collect(session_id=1)

        self.assertEqual(result, {"order_no": "T123"})
        workflow_service.get_session_state.assert_called_once_with(42, "9001")

    def test_two_tasks_active_wins_on_collision(self) -> None:
        completed_task = {
            "id": 11,
            "session_id": 1,
            "status": "COMPLETED",
            "business_refs": {},
            "chatflow_id": 42,
            "chatflow_session_id": 9001,
        }
        active_task = {
            "id": 12,
            "session_id": 1,
            "status": "RUNNING",
            "business_refs": {},
            "chatflow_id": 42,
            "chatflow_session_id": 9002,
        }
        repository = MagicMock()
        repository.list_tasks.return_value = [completed_task, active_task]
        repository.get_active_task.return_value = active_task

        def _get_state(chatflow_id: int, session_id: str) -> dict[str, object]:
            if session_id == "9001":
                return {"variables": {"conversation": {"name": "old"}}}
            return {"variables": {"conversation": {"name": "new"}}}

        workflow_service = MagicMock()
        workflow_service.get_session_state.side_effect = _get_state
        agg = RuntimeLabBusinessContextAggregator(repository, workflow_service)

        result = agg.collect(session_id=1)

        self.assertEqual(result, {"name": "new"})

    def test_missing_chatflow_refs_falls_back_to_business_refs(self) -> None:
        repository = MagicMock()
        repository.list_tasks.return_value = [
            {
                "id": 11,
                "session_id": 1,
                "status": "COMPLETED",
                "business_refs": {"order_no": "TX1"},
                "chatflow_id": None,
                "chatflow_session_id": None,
            }
        ]
        repository.get_active_task.return_value = None
        workflow_service = MagicMock()
        agg = RuntimeLabBusinessContextAggregator(repository, workflow_service)

        result = agg.collect(session_id=1)

        self.assertEqual(result, {"order_no": "TX1"})
        workflow_service.get_session_state.assert_not_called()

    def test_bizerror_falls_back_to_business_refs(self) -> None:
        repository = MagicMock()
        repository.list_tasks.return_value = [
            {
                "id": 11,
                "session_id": 1,
                "status": "COMPLETED",
                "business_refs": {"order_no": "TX2", "phone": "13800000000"},
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

        result = agg.collect(session_id=1)

        self.assertEqual(result, {"order_no": "TX2", "phone": "13800000000"})

    def test_chatflow_conversation_wins_over_business_refs_for_same_key(self) -> None:
        """Regex-only slots survive while chatflow conversation overrides on collision."""
        repository = MagicMock()
        repository.list_tasks.return_value = [
            {
                "id": 11,
                "session_id": 1,
                "status": "COMPLETED",
                # business_refs has both order_no (regex-only) and name (will be overridden)
                "business_refs": {"order_no": "REGEX-ORDER", "name": "OldName"},
                "chatflow_id": 42,
                "chatflow_session_id": 9001,
            }
        ]
        repository.get_active_task.return_value = None
        workflow_service = MagicMock()
        workflow_service.get_session_state.return_value = {
            "variables": {"conversation": {"name": "NewName"}}
        }
        agg = RuntimeLabBusinessContextAggregator(repository, workflow_service)

        result = agg.collect(session_id=1)

        # order_no survives (regex-only slot not in chatflow conversation)
        # name overridden by chatflow conversation
        self.assertEqual(result, {"order_no": "REGEX-ORDER", "name": "NewName"})


if __name__ == "__main__":
    unittest.main()
