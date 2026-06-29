"""Spec 213.3.5c (narrow) — _sop_checkpoint_from_row rebuilds the ``__chatflow``
meta in :class:`SopCheckpoint` from the task ref columns.

Cycle 1 attempted to also migrate ``collected`` to ``aggregator.collect(...)``,
but verified failure of audit assumption R1 (aggregator output is
session-scoped, crossing SOP boundaries — see ``13.3.5/AUDIT.md`` §9 R1).
Cycle 2 narrows the migration to ``__chatflow`` only; ``collected`` continues
to be sourced from ``checkpoint.collected`` until slice 213.3.5d pairs the
migration with a ``_adapter_request`` rewrite that respects
``SOP_CONTEXT_KEYS[sop_id]``.

After this sub-slice:
- ``SopCheckpoint.scoped_variables['__chatflow']`` is sourced from the task's
  first-class ref columns (``chatflow_id`` / ``chatflow_run_id`` etc.) added in
  slice 213.3.1; legacy ``checkpoint.scoped_variables.__chatflow`` is only
  consulted when the task carries no refs.
- ``SopCheckpoint.collected`` continues to come from ``checkpoint.collected``
  (deferred to slice 213.3.5d).
- ``current_step`` still reads from the checkpoint row (banned in 213.3.5e).

Audit refs:
- artifacts/slices/213-runtime-async-default-invocation-gateway/213.3.5/AUDIT.md §1.A/B/C, §3, §9 R1, §8 213.3.5c row
"""

from __future__ import annotations

import unittest
from typing import Any

from app.modules.runtime_lab.domain.service import _sop_checkpoint_from_row


def _checkpoint_row(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": 501,
        "task_id": 301,
        "session_id": 1001,
        "current_step": "collect_order_no",
        "pending_prompt": "",
        "collected": {},
        "scoped_variables": {},
        "version": 1,
    }
    base.update(overrides)
    return base


def _task_row(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": 301,
        "session_id": 1001,
        "sop_id": "refund_ticket",
        "current_step": "collect_order_no",
        "chatflow_id": None,
        "chatflow_session_id": None,
        "chatflow_run_id": None,
        "chatflow_event_id": None,
        "chatflow_checkpoint_id": None,
        "runtime_version": None,
    }
    base.update(overrides)
    return base


class SopCheckpointFromRowRebuildTest(unittest.TestCase):
    def test_collected_remains_from_checkpoint_in_213_3_5c(self) -> None:
        """Cycle 2 narrow scope: collected stays sourced from checkpoint row.

        Migrating collected to aggregator is deferred to 213.3.5d because the
        aggregator output is session-scoped (crosses SOP boundaries), so
        adopting it without a SOP_CONTEXT_KEYS filter leaks fields like
        ``passenger_count='团队'`` from group_booking into refund_ticket.
        """
        task = _task_row()
        checkpoint = _checkpoint_row(collected={"order_no": "CHECKPOINT"})

        result = _sop_checkpoint_from_row(task, checkpoint)

        assert result is not None
        self.assertEqual(result.collected, {"order_no": "CHECKPOINT"})

    def test_chatflow_meta_comes_from_task_ref_columns(self) -> None:
        task = _task_row(
            chatflow_id=42,
            chatflow_session_id=9001,
            chatflow_run_id=777,
            chatflow_event_id=888,
            chatflow_checkpoint_id=999,
            runtime_version="v2",
        )
        # Stale __chatflow in the checkpoint scoped_variables — must be ignored
        # in favor of the task ref columns.
        checkpoint = _checkpoint_row(
            scoped_variables={
                "__chatflow": {
                    "chatflowId": 99,
                    "runId": 1,
                }
            }
        )

        result = _sop_checkpoint_from_row(task, checkpoint)

        assert result is not None
        meta = result.scoped_variables.get("__chatflow")
        self.assertIsNotNone(meta)
        assert isinstance(meta, dict)
        self.assertEqual(meta["chatflowId"], 42)
        self.assertEqual(meta["runId"], 777)
        self.assertEqual(meta["sessionId"], 9001)
        self.assertEqual(meta["eventId"], 888)
        self.assertEqual(meta["checkpointId"], 999)
        self.assertEqual(meta["runtimeVersion"], "v2")

    def test_current_step_still_from_checkpoint(self) -> None:
        task = _task_row(current_step="collect_order_no")
        checkpoint = _checkpoint_row(current_step="confirm")

        result = _sop_checkpoint_from_row(task, checkpoint)

        assert result is not None
        self.assertEqual(result.current_step, "confirm")
        self.assertEqual(result.current_node_id, "confirm")

    def test_no_task_refs_falls_back_to_checkpoint_scoped_variables(self) -> None:
        """When the task carries no refs, legacy ``__chatflow`` in the checkpoint
        ``scoped_variables`` is retained as the transition fallback.
        """
        task = _task_row(chatflow_id=None, chatflow_run_id=None)
        legacy_meta = {
            "chatflowId": 99,
            "runId": 1,
            "runtimeVersion": "v2",
        }
        checkpoint = _checkpoint_row(scoped_variables={"__chatflow": legacy_meta})

        result = _sop_checkpoint_from_row(task, checkpoint)

        assert result is not None
        meta = result.scoped_variables.get("__chatflow")
        self.assertIsNotNone(meta)
        assert isinstance(meta, dict)
        self.assertEqual(meta["chatflowId"], 99)
        self.assertEqual(meta["runId"], 1)


if __name__ == "__main__":
    unittest.main()
