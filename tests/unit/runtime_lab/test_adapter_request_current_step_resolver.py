import unittest
from unittest.mock import MagicMock

from app.modules.runtime_lab.domain.service import RuntimeLabService


class AdapterRequestCurrentStepResolverTest(unittest.TestCase):
    def test_adapter_request_checkpoint_uses_side_channel_when_checkpoint_row_empty(self) -> None:
        repository = MagicMock()
        aggregator = MagicMock()
        aggregator.collect.return_value = {}
        aggregator.task_current_step.return_value = "confirm"
        service = RuntimeLabService(repository, aggregator=aggregator)

        request = service._adapter_request(
            session_id=1,
            sop_id="refund_ticket",
            task={"id": 10, "session_id": 1, "current_step": "collect_order_no"},
            checkpoint_row={
                "id": 20,
                "task_id": 10,
                "session_id": 1,
                "current_step": "",
                "pending_prompt": "",
                "collected": {},
                "scoped_variables": {},
                "version": 1,
            },
        )

        assert request.checkpoint is not None
        self.assertEqual(request.checkpoint.current_step, "confirm")
        self.assertEqual(request.checkpoint.current_node_id, "confirm")

    def test_adapter_request_checkpoint_prefers_runtime_step(self) -> None:
        repository = MagicMock()
        aggregator = MagicMock()
        aggregator.collect.return_value = {}
        aggregator.task_current_step.return_value = "collect_order_no"
        service = RuntimeLabService(
            repository,
            aggregator=aggregator,
            current_step_runtime=_RuntimeResult({"checkpoint": {"pendingNodeKey": "confirm"}}),
        )

        request = service._adapter_request(
            session_id=1,
            sop_id="refund_ticket",
            task={
                "id": 10,
                "session_id": 1,
                "current_step": "collect_order_no",
                "chatflow_run_id": 777,
            },
            checkpoint_row={
                "id": 20,
                "task_id": 10,
                "session_id": 1,
                "current_step": "collect_order_no",
                "pending_prompt": "",
                "collected": {},
                "scoped_variables": {},
                "version": 1,
            },
        )

        assert request.checkpoint is not None
        self.assertEqual(request.checkpoint.current_step, "confirm")
        self.assertEqual(request.checkpoint.current_node_id, "confirm")


class _RuntimeResult:
    def __init__(self, result: dict) -> None:
        self._result = result

    def get_result(self, run_id: int) -> dict:
        return self._result


if __name__ == "__main__":
    unittest.main()
