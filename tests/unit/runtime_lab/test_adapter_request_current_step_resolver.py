import unittest
from unittest.mock import MagicMock

from app.modules.runtime_lab.domain.service import RuntimeLabService


class AdapterRequestCurrentStepResolverTest(unittest.TestCase):
    def test_adapter_request_checkpoint_is_none_without_child_runtime_step(self) -> None:
        repository = MagicMock()
        repository.list_events.return_value = []
        aggregator = MagicMock()
        aggregator.collect.return_value = {}
        aggregator.task_current_step.return_value = "confirm"
        service = RuntimeLabService(repository, aggregator=aggregator)

        request = service._adapter_request(
            session_id=1,
            sop_id="refund_ticket",
            task={"id": 10, "session_id": 1, "current_step": "collect_order_no"},
        )

        self.assertIsNone(request.checkpoint)

    def test_adapter_request_checkpoint_prefers_runtime_step(self) -> None:
        repository = MagicMock()
        repository.list_events.return_value = []
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
