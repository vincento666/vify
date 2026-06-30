import unittest
from unittest.mock import MagicMock

from app.modules.runtime_lab.domain.service import RuntimeLabService


class RuntimeLabCurrentStepResolverTest(unittest.TestCase):
    def test_prefers_runtime_checkpoint_pending_node_over_overlay_and_db(self) -> None:
        repository = MagicMock()
        repository.get_latest_checkpoint.return_value = {"current_step": "collect_order_no"}
        aggregator = MagicMock()
        aggregator.collect.return_value = {}
        aggregator.task_current_step.return_value = "collect_order_no"
        runtime = _RuntimeResult({"checkpoint": {"pendingNodeKey": "confirm"}})
        service = RuntimeLabService(repository, aggregator=aggregator, current_step_runtime=runtime)

        result = service._latest_checkpoint_with_overlay_step(
            {
                "id": 10,
                "current_step": "collect_order_no",
                "chatflow_run_id": 777,
            }
        )

        self.assertEqual(result["current_step"], "confirm")
        runtime.assert_called_with(777)

    def test_falls_back_to_side_channel_when_runtime_errors(self) -> None:
        repository = MagicMock()
        repository.get_latest_checkpoint.return_value = {"current_step": "collect_order_no"}
        aggregator = MagicMock()
        aggregator.collect.return_value = {}
        aggregator.task_current_step.return_value = "confirm"
        runtime = _RuntimeError()
        service = RuntimeLabService(repository, aggregator=aggregator, current_step_runtime=runtime)

        result = service._latest_checkpoint_with_overlay_step(
            {
                "id": 10,
                "current_step": "collect_order_no",
                "chatflow_run_id": 777,
            }
        )

        self.assertEqual(result["current_step"], "confirm")

    def test_falls_back_to_checkpoint_then_task(self) -> None:
        repository = MagicMock()
        repository.get_latest_checkpoint.return_value = {"current_step": "confirm"}
        aggregator = MagicMock()
        aggregator.collect.return_value = {}
        aggregator.task_current_step.return_value = None
        service = RuntimeLabService(repository, aggregator=aggregator, current_step_runtime=None)

        result = service._latest_checkpoint_with_overlay_step(
            {"id": 10, "current_step": "collect_order_no", "chatflow_run_id": None}
        )
        self.assertEqual(result["current_step"], "confirm")

        repository.get_latest_checkpoint.return_value = None
        result = service._latest_checkpoint_with_overlay_step(
            {"id": 10, "current_step": "collect_order_no", "chatflow_run_id": None}
        )
        self.assertEqual(result["current_step"], "collect_order_no")


class _RuntimeResult:
    def __init__(self, result: dict) -> None:
        self._result = result
        self.calls: list[int] = []

    def get_result(self, run_id: int) -> dict:
        self.calls.append(run_id)
        return self._result

    def assert_called_with(self, run_id: int) -> None:
        assert self.calls == [run_id]


class _RuntimeError:
    def get_result(self, run_id: int) -> dict:
        raise RuntimeError("runtime unavailable")


if __name__ == "__main__":
    unittest.main()
