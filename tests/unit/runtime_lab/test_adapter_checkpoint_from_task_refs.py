"""Spec 213.3.5g — adapter checkpoints are rebuilt from task refs in memory."""

import unittest
from unittest.mock import MagicMock

from app.modules.runtime_lab.domain.aggregator import RuntimeLabBusinessContextAggregator
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository


class AdapterCheckpointFromTaskRefsTest(unittest.TestCase):
    def test_checkpoint_meta_comes_from_task_ref_columns(self) -> None:
        service = _service()

        checkpoint = service._adapter_checkpoint_from_task(  # noqa: SLF001
            _task_row(
                chatflow_id=42,
                chatflow_session_id=9001,
                chatflow_run_id=777,
                chatflow_event_id=888,
                chatflow_checkpoint_id=999,
                runtime_version="v2",
            ),
        )

        assert checkpoint is not None
        self.assertEqual(checkpoint.current_step, "confirm")
        self.assertEqual(checkpoint.current_node_id, "confirm")
        self.assertEqual(checkpoint.collected, {})
        meta = checkpoint.scoped_variables.get("__chatflow")
        self.assertIsNotNone(meta)
        assert isinstance(meta, dict)
        self.assertEqual(meta["chatflowId"], 42)
        self.assertEqual(meta["runId"], 777)
        self.assertEqual(meta["sessionId"], 9001)
        self.assertEqual(meta["eventId"], 888)
        self.assertEqual(meta["checkpointId"], 999)
        self.assertEqual(meta["runtimeVersion"], "v2")

    def test_returns_none_when_no_current_step_source_exists(self) -> None:
        service = _service()

        checkpoint = service._adapter_checkpoint_from_task(  # noqa: SLF001
            _task_row(),
        )

        self.assertIsNone(checkpoint)


def _service() -> RuntimeLabService:
    repository = MagicMock(spec=RuntimeLabRepository)
    aggregator = RuntimeLabBusinessContextAggregator(repository, None)
    return RuntimeLabService(
        repository,
        aggregator=aggregator,
        current_step_runtime=_RuntimeResult({"checkpoint": {"pendingNodeKey": "confirm"}}),
    )


class _RuntimeResult:
    def __init__(self, result: dict[str, object]) -> None:
        self._result = result

    def get_result(self, _run_id: int) -> dict[str, object]:
        return self._result


def _task_row(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": 301,
        "session_id": 1001,
        "sop_id": "refund_ticket",
        "chatflow_id": None,
        "chatflow_session_id": None,
        "chatflow_run_id": None,
        "chatflow_event_id": None,
        "chatflow_checkpoint_id": None,
        "runtime_version": None,
    }
    base.update(overrides)
    return base


if __name__ == "__main__":
    unittest.main()
