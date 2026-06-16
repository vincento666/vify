import unittest

from app.modules.customer_assistant.domain.models import TaskItem, TaskLedger, TaskStatus


class CustomerAssistantDomainModelTest(unittest.TestCase):
    def test_task_ledger_finds_by_key_and_lists_active_tasks(self) -> None:
        refund = TaskItem(
            id=1,
            session_id=10,
            task_key="refund_ticket",
            task_type="REFUND",
            business_key="refund_ticket",
            short_id="RETI",
            status=TaskStatus.WAITING,
            worker_type="chatflow_sop",
            worker_ref="refund_ticket",
        )
        done = TaskItem(
            id=2,
            session_id=10,
            task_key="baggage_qa",
            task_type="QA",
            business_key="baggage_qa",
            short_id="BAQA",
            status=TaskStatus.COMPLETED,
            worker_type="stub_qa",
            worker_ref="baggage_allowance",
        )

        ledger = TaskLedger(session_id=10, tasks=(refund, done))

        self.assertEqual(ledger.by_key("refund_ticket"), refund)
        self.assertEqual(ledger.by_key("missing"), None)
        self.assertEqual(ledger.active_tasks(), (refund,))


if __name__ == "__main__":
    unittest.main()
