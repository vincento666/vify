import unittest

from app.modules.runtime_lab.domain.router import RuntimeLabRouter
from app.modules.runtime_lab.domain.sop import MockSopAdapter


class RuntimeLabRouterTest(unittest.TestCase):
    def test_strong_keyword_starts_sop_when_no_active_task(self) -> None:
        decision = RuntimeLabRouter().decide("我要退票")

        self.assertEqual(decision.action, "START_SOP")
        self.assertEqual(decision.target_sop_id, "refund_ticket")
        self.assertEqual(decision.matched_keyword, "退票")
        self.assertIn("strong keyword", decision.reason)

    def test_active_task_defaults_to_continue_without_strong_switch(self) -> None:
        decision = RuntimeLabRouter().decide(
            "TK-100",
            active_task={"id": 7, "sop_id": "refund_ticket", "current_step": "collect_order_no"},
        )

        self.assertEqual(decision.action, "CONTINUE_ACTIVE_SOP")
        self.assertEqual(decision.active_task_id, 7)
        self.assertIsNone(decision.target_sop_id)

    def test_strong_different_sop_trigger_returns_switch_decision(self) -> None:
        decision = RuntimeLabRouter(MockSopAdapter()).decide(
            "我要开发票",
            active_task={"id": 7, "sop_id": "refund_ticket", "current_step": "collect_order_no"},
        )

        self.assertEqual(decision.action, "SUSPEND_AND_START")
        self.assertEqual(decision.active_task_id, 7)
        self.assertEqual(decision.target_sop_id, "invoice_apply")
        self.assertEqual(decision.matched_keyword, "发票")

    def test_no_active_and_no_keyword_returns_no_match(self) -> None:
        decision = RuntimeLabRouter().decide("你好")

        self.assertEqual(decision.action, "NO_MATCH")
        self.assertIn("No strong", decision.reason)
