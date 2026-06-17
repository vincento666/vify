from contextlib import contextmanager
import unittest
from collections.abc import Iterator

from sqlalchemy.orm import Session

from tests.support.mysql import mysql8_session
from app.modules.customer_assistant.domain.service import CustomerAssistantService
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository
from app.modules.customer_assistant.infra.schema import (
    customer_assistant_tables,
    register_customer_assistant_tables,
)


class CustomerAssistantOperatorTurnModeTest(unittest.TestCase):
    def test_operator_refund_question_is_recommendation_only(self) -> None:
        with _session() as session:
            service = CustomerAssistantService(CustomerAssistantRepository(session))
            assistant_session = service.create_session()
            session_id = int(assistant_session["id"])

            result = service.handle_turn(
                session_id,
                "客户说要退票，我该怎么处理？",
                idempotency_key="operator-refund-question",
                actor="operator",
            )
            tasks = service.list_tasks(session_id)["list"]
            events = service.list_events(session_id)["list"]

        event_types = [event["type"] for event in events]
        run_started = next(event for event in events if event["type"] == "run_started")
        self.assertEqual(tasks, [])
        self.assertEqual(result["taskSummaries"], [])
        self.assertEqual(result["replyType"], "OPERATOR_RECOMMENDATION")
        self.assertIn("operator_turn_classified", event_types)
        self.assertEqual(run_started["payload"]["turnMode"], "operator_recommendation_turn")
        self.assertNotIn("task_recognized", event_types)
        self.assertNotIn("task_added", event_types)
        self.assertNotIn("task_started", event_types)
        self.assertNotIn("worker_started", event_types)
        self.assertTrue(result["operatorRecommendation"].strip())

    def test_customer_refund_turn_keeps_task_behavior(self) -> None:
        with _session() as session:
            service = CustomerAssistantService(CustomerAssistantRepository(session))
            assistant_session = service.create_session()
            session_id = int(assistant_session["id"])

            result = service.handle_turn(session_id, "我要退票", idempotency_key="customer-refund")
            events = service.list_events(session_id)["list"]

        event_types = [event["type"] for event in events]
        self.assertEqual([task["taskKey"] for task in result["taskSummaries"]], ["refund_ticket"])
        self.assertIn("task_recognized", event_types)
        self.assertIn("task_added", event_types)
        self.assertIn("worker_started", event_types)

    def test_operator_advice_uses_read_only_ledger_and_event_context(self) -> None:
        with _session() as session:
            service = CustomerAssistantService(CustomerAssistantRepository(session))
            assistant_session = service.create_session()
            session_id = int(assistant_session["id"])
            service.handle_turn(session_id, "我要退票", idempotency_key="customer-context")

            result = service.handle_turn(
                session_id,
                "现在这单坐席侧下一步怎么处理？",
                idempotency_key="operator-advice",
                actor="operator",
            )
            tasks = service.list_tasks(session_id)["list"]
            events = service.list_events(session_id)["list"]

        event_types = [event["type"] for event in events]
        self.assertEqual([task["taskKey"] for task in tasks], ["refund_ticket"])
        self.assertEqual(result["taskSummaries"][0]["taskKey"], "refund_ticket")
        self.assertIn("refund_ticket", result["operatorRecommendation"])
        self.assertIn("event", result["operatorRecommendation"].lower())
        self.assertTrue(
            "sop" in result["operatorRecommendation"].lower()
            or "chatflow" in result["operatorRecommendation"].lower()
        )
        self.assertTrue(any("knowledge" in warning.lower() for warning in result["warnings"]))
        self.assertIn("operator_advisory_context_packed", event_types)
        self.assertIn("operator_advisory_harness_summarized", event_types)
        self.assertIn("operator_recommendation_generated", event_types)
        harness_event = next(event for event in events if event["type"] == "operator_advisory_harness_summarized")
        self.assertEqual(harness_event["payload"]["readOnly"], True)

    def test_operator_proposed_task_command_requires_confirm_before_mutating_ledger(self) -> None:
        with _session() as session:
            service = CustomerAssistantService(CustomerAssistantRepository(session))
            assistant_session = service.create_session()
            session_id = int(assistant_session["id"])

            result = service.handle_turn(
                session_id,
                "请把这个客户需求加入退票任务",
                idempotency_key="operator-propose-refund-task",
                actor="operator",
            )
            tasks_before = service.list_tasks(session_id)["list"]
            action = result["proposedActions"][0]
            confirmed = service.confirm_action(int(action["id"]))
            tasks_after = service.list_tasks(session_id)["list"]
            events = service.list_events(session_id)["list"]

        event_types = [event["type"] for event in events]
        self.assertEqual(tasks_before, [])
        self.assertEqual(action["actionType"], "PROPOSED_TASK_COMMAND")
        self.assertEqual(action["status"], "PENDING")
        self.assertEqual(confirmed["status"], "CONFIRMED")
        self.assertEqual([task["taskKey"] for task in tasks_after], ["refund_ticket"])
        self.assertIn("proposed_task_command_created", event_types)
        self.assertIn("proposed_task_command_confirmed", event_types)
        self.assertIn("task_added", event_types)


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session("customer_assistant_operator_turn", tables=customer_assistant_tables(), register=register_customer_assistant_tables) as session:
        yield session


if __name__ == "__main__":
    unittest.main()
