from contextlib import contextmanager
import unittest
from collections.abc import Iterator

from sqlalchemy.orm import Session

from tests.support.mysql import mysql8_session
from app.modules.customer_assistant.domain.models import TaskCommand, TaskCommandType
from app.modules.customer_assistant.domain.turn_coordinator import TurnObservation
from app.modules.customer_assistant.domain.react_worker import (
    FakeReactWorkerModel,
    ReactModelAction,
    RestrictedReactWorker,
)
from app.modules.customer_assistant.domain.scheduler import LocalWorkerScheduler
from app.modules.customer_assistant.domain.service import CustomerAssistantService
from app.modules.customer_assistant.domain.worker_registry import ReactWorkerConfig
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository
from app.modules.customer_assistant.infra.schema import (
    customer_assistant_tables,
    register_customer_assistant_tables,
)


class CustomerAssistantReactWorkerIntegrationTest(unittest.TestCase):
    def test_react_worker_returns_normal_worker_result_and_persists_events(self) -> None:
        with _session() as session:
            service = CustomerAssistantService(
                CustomerAssistantRepository(session),
                core=_ReactTaskCore(),
                scheduler=LocalWorkerScheduler(
                    {
                        "react_worker": RestrictedReactWorker(
                            config=_config(),
                            model=FakeReactWorkerModel(
                                [
                                    ReactModelAction.request_tool("lookup_order", {"orderNo": "TK-100"}),
                                    ReactModelAction.final(
                                        operator_recommendation="Order TK-100 is refundable.",
                                        customer_reply_draft="订单 TK-100 可退票。",
                                    ),
                                ]
                            ),
                            tools={"lookup_order": lambda args: {"orderNo": args["orderNo"], "status": "ok"}},
                        )
                    }
                ),
            )
            assistant_session = service.create_session()

            result = service.handle_turn(int(assistant_session["id"]), "查 TK-100", idempotency_key="react")
            events = service.list_events(int(assistant_session["id"]))["list"]

        event_types = [event["type"] for event in events]
        react_events = [event for event in events if event["source"] == "react_worker"]
        self.assertEqual(result["taskSummaries"][0]["workerType"], "react_worker")
        self.assertIn("Order [REDACTED] is refundable.", result["operatorRecommendation"])
        self.assertNotIn("TK-100", result["operatorRecommendation"])
        self.assertIn("react_worker_started", event_types)
        self.assertIn("react_worker_completed", event_types)
        self.assertTrue(all(event["visibility"] == "debug" for event in react_events))

    def test_high_risk_react_write_is_persisted_as_pending_proposed_action(self) -> None:
        with _session() as session:
            service = CustomerAssistantService(
                CustomerAssistantRepository(session),
                core=_ReactTaskCore(),
                scheduler=LocalWorkerScheduler(
                    {
                        "react_worker": RestrictedReactWorker(
                            config=_config(allowed_tools=("submit_refund",)),
                            model=FakeReactWorkerModel(
                                [
                                    ReactModelAction.request_tool(
                                        "submit_refund",
                                        {"orderNo": "TK-100"},
                                        risk="write",
                                    )
                                ]
                            ),
                            tools={"submit_refund": lambda _args: {"shouldNotExecute": True}},
                        )
                    }
                ),
            )
            assistant_session = service.create_session()

            result = service.handle_turn(int(assistant_session["id"]), "提交退票", idempotency_key="react-write")

        self.assertEqual(result["taskSummaries"][0]["status"], "WAITING")
        self.assertEqual(result["proposedActions"][0]["status"], "PENDING")
        self.assertEqual(result["proposedActions"][0]["actionType"], "submit_refund")


class _ReactTaskCore:
    def run(self, context, action_handler, finalizer):
        commands = [
            TaskCommand(
                TaskCommandType.ADD_TASK,
                task_key="refund_status:TK-100",
                task_type="refund_status",
                business_key="TK-100",
                worker_type="react_worker",
                worker_ref="refund_status_react",
            )
        ]
        action_result = action_handler(commands)
        return finalizer(
            TurnObservation(commands=tuple(commands), action_result=action_result)
        )


def _config(allowed_tools: tuple[str, ...] = ("lookup_order", "submit_refund")) -> ReactWorkerConfig:
    return ReactWorkerConfig(
        worker_ref="refund_status_react",
        task_type="refund_status",
        allowed_tools=allowed_tools,
        max_iterations=3,
        timeout_ms=1000,
    )


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session("customer_assistant_react_worker", tables=customer_assistant_tables(), register=register_customer_assistant_tables) as session:
        yield session


if __name__ == "__main__":
    unittest.main()
