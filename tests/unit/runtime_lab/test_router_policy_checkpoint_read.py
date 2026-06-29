"""Spec 213.3.5b — router and policy read current_step from checkpoint, not task.

After spec 213.3.5e bans task.current_step writes, the column becomes empty.
This sub-slice moves the dispatch reads to latest_checkpoint.current_step
(which is still being written in 213.3.5b—213.3.5d transition window).

Audit refs:
- artifacts/slices/213-runtime-async-default-invocation-gateway/213.3.5/AUDIT.md §1.A #1-2
- §8 213.3.5b row
"""

from __future__ import annotations

import unittest
from typing import Any

from app.modules.runtime_lab.domain.candidates import (
    CandidateType,
    RouteCandidate,
    ScoreBreakdown,
)
from app.modules.runtime_lab.domain.classifier import ClassifierResult
from app.modules.runtime_lab.domain.policy import PolicyGate
from app.modules.runtime_lab.domain.router import RuntimeLabRouter


class _RecordingAdapter:
    """Captures every (sop_id, step_id) pair passed to is_interruptible."""

    def __init__(self, interruptible_steps: set[tuple[str, str]]) -> None:
        self._interruptible = interruptible_steps
        self.calls: list[tuple[str, str]] = []

    def is_interruptible(self, sop_id: str, step_id: str) -> bool:
        self.calls.append((sop_id, step_id))
        return (sop_id, step_id) in self._interruptible


def _sop_intent_candidate(target_id: str, score: float) -> RouteCandidate:
    return RouteCandidate(
        candidate_id=f"sop_intent::{target_id}",
        candidate_type=CandidateType.SOP_INTENT,
        target_id=target_id,
        display_name=target_id,
        source="test",
        score=score,
        score_breakdown=ScoreBreakdown(keyword=score, alias=0.0, semantic=0.0),
        matched_terms=("发票",),
        risk_level="low",
        requires_classifier=False,
        reason="test fixture",
    )


class RouterReadsCheckpointCurrentStepTest(unittest.TestCase):
    """router._classify_with_keyword (router.py:80) must read current_step from
    the latest checkpoint when supplied, not from task.current_step."""

    def test_router_classify_uses_checkpoint_current_step_for_interruptibility(self) -> None:
        # Task carries a stale non-interruptible step; checkpoint shows the real
        # current step (interruptible). Adapter must be consulted with the
        # checkpoint's value.
        adapter = _RecordingAdapter(
            interruptible_steps={("refund_ticket", "collect_order_no")},
        )
        router = RuntimeLabRouter(adapter)
        active_task: dict[str, Any] = {
            "id": 7,
            "sop_id": "refund_ticket",
            "current_step": "confirm",  # stale, non-interruptible
        }
        latest_checkpoint: dict[str, Any] = {
            "task_id": 7,
            "current_step": "collect_order_no",  # fresh, interruptible
        }

        decision = router.decide(
            "我要开发票",
            active_task=active_task,
            latest_checkpoint=latest_checkpoint,
        )

        self.assertEqual(decision.action, "SUSPEND_AND_START")
        self.assertEqual(decision.target_sop_id, "invoice_apply")
        self.assertEqual(decision.active_task_id, 7)
        # Adapter saw the checkpoint's step, not the task's stale step.
        self.assertIn(("refund_ticket", "collect_order_no"), adapter.calls)
        self.assertNotIn(("refund_ticket", "confirm"), adapter.calls)


class PolicyReadsCheckpointCurrentStepTest(unittest.TestCase):
    """policy._switch_decision (policy.py:172) must read current_step from
    the latest checkpoint when supplied, not from task.current_step."""

    def test_policy_classify_uses_checkpoint_current_step_for_interruptibility(self) -> None:
        adapter = _RecordingAdapter(
            interruptible_steps={("refund_ticket", "collect_order_no")},
        )
        gate = PolicyGate(adapter)
        candidate = _sop_intent_candidate("invoice_apply", score=0.92)
        candidates = (candidate,)
        result = ClassifierResult(
            selected_action="SUSPEND_AND_START",
            selected_candidate_id=candidate.candidate_id,
            confidence=0.92,
            rationale="test rationale",
            needs_clarification=False,
            clarification_question=None,
        )
        active_task: dict[str, Any] = {
            "id": 11,
            "sop_id": "refund_ticket",
            "current_step": "confirm",  # stale
        }
        latest_checkpoint: dict[str, Any] = {
            "task_id": 11,
            "current_step": "collect_order_no",  # fresh, interruptible
        }

        decision = gate.classifier_decision(
            result,
            candidates,
            active_task,
            suspended_count=0,
            latest_checkpoint=latest_checkpoint,
        )

        self.assertEqual(decision.action, "SUSPEND_AND_START")
        self.assertEqual(decision.target_sop_id, "invoice_apply")
        self.assertEqual(decision.active_task_id, 11)
        self.assertIn(("refund_ticket", "collect_order_no"), adapter.calls)
        self.assertNotIn(("refund_ticket", "confirm"), adapter.calls)


class FallbackTest(unittest.TestCase):
    """During the 213.3.5b—213.3.5d transition window, callers may not yet
    pass a checkpoint. Router/policy must fall back to task.current_step so
    existing behavior is preserved."""

    def test_router_falls_back_to_task_current_step_when_no_checkpoint(self) -> None:
        adapter = _RecordingAdapter(
            interruptible_steps={("refund_ticket", "collect_order_no")},
        )
        router = RuntimeLabRouter(adapter)
        active_task: dict[str, Any] = {
            "id": 9,
            "sop_id": "refund_ticket",
            "current_step": "collect_order_no",
        }

        decision = router.decide(
            "我要开发票",
            active_task=active_task,
            latest_checkpoint=None,
        )

        self.assertEqual(decision.action, "SUSPEND_AND_START")
        self.assertIn(("refund_ticket", "collect_order_no"), adapter.calls)


if __name__ == "__main__":
    unittest.main()
