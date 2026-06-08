import unittest

from app.modules.runtime_lab.domain.sop import MockSopAdapter, mock_sop_manifests


class MockSopAdapterTest(unittest.TestCase):
    def test_start_collect_confirm_and_complete_mock_sop(self) -> None:
        manifests = mock_sop_manifests()
        adapter = MockSopAdapter(manifests)

        self.assertEqual(
            set(manifests),
            {
                "flight_booking",
                "fare_quote",
                "group_booking",
                "ancillary_sales",
                "refund_ticket",
                "change_flight",
                "passenger_info_change",
                "invoice_apply",
                "baggage_service",
                "seat_checkin",
                "flight_status",
                "special_assistance",
                "pet_cabin",
                "irregular_flight",
                "membership_service",
            },
        )

        started = adapter.start("refund_ticket")
        self.assertEqual(started.current_step, "collect_order_no")
        self.assertIn("订单号", started.reply)
        self.assertTrue(adapter.is_interruptible("refund_ticket", "collect_order_no"))

        collected = adapter.continue_task(
            sop_id="refund_ticket",
            current_step=started.current_step,
            message="TK-100",
            collected=started.collected,
        )
        self.assertEqual(collected.current_step, "confirm")
        self.assertEqual(collected.collected["order_no"], "TK-100")
        self.assertEqual(collected.checkpoint["current_step"], "confirm")
        self.assertFalse(adapter.is_interruptible("refund_ticket", "confirm"))

        completed = adapter.continue_task(
            sop_id="refund_ticket",
            current_step=collected.current_step,
            message="确认",
            collected=collected.collected,
        )
        self.assertTrue(completed.completed)
        self.assertEqual(completed.current_step, "completed")
        self.assertEqual(completed.checkpoint["status"], "COMPLETED")
        self.assertIn("退票", completed.reply)
