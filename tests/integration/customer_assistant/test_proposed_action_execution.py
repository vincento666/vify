from contextlib import contextmanager
import unittest
from collections.abc import Iterator

from sqlalchemy.orm import Session

from tests.support.mysql import mysql8_session
from app.core.errors import BizError
from app.modules.customer_assistant.domain.action_executor import MockActionExecutionResult, MockActionExecutorRegistry
from app.modules.customer_assistant.domain.service import CustomerAssistantService
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository
from app.modules.customer_assistant.infra.schema import customer_assistant_tables, register_customer_assistant_tables


class CustomerAssistantProposedActionExecutionTest(unittest.TestCase):
    def test_unsupported_action_execution_persists_failed_audit_evidence(self) -> None:
        with _session() as session:
            repository = CustomerAssistantRepository(session)
            assistant_session = repository.create_session(context={"customerId": "C-301"})
            run, _ = repository.create_run(
                int(assistant_session["id"]),
                idempotency_key="execute-failed-1",
                request_hash="execute-failed-hash",
                input_payload={"message": "执行未知动作"},
            )
            action = repository.upsert_proposed_action(
                session_id=int(assistant_session["id"]),
                run_id=int(run["id"]),
                task_id=None,
                action_key="execute-failed:unknown",
                action_type="unknown_write",
                title="未知写动作",
                payload={"orderNo": "TK-301"},
            )
            repository.update_proposed_action_status(int(action["id"]), "CONFIRMED")
            service = CustomerAssistantService(repository)

            executed = service.execute_action(int(action["id"]))
            events = repository.list_events(int(assistant_session["id"]))

        self.assertEqual(executed["status"], "FAILED")
        self.assertEqual(executed["result"]["executorRef"], "unsupported_action_mock")
        self.assertEqual(executed["result"]["error"]["code"], "UNSUPPORTED_ACTION")
        self.assertEqual(executed["result"]["audit"]["semanticCode"], "UNSUPPORTED_ACTION")
        self.assertIn("proposed_action_failed", [event["type"] for event in events])

    def test_execute_does_not_call_executor_when_atomic_claim_is_stale(self) -> None:
        with _session() as session:
            repository = _StaleClaimRepository(session)
            assistant_session = repository.create_session(context={"customerId": "C-300"})
            run, _ = repository.create_run(
                int(assistant_session["id"]),
                idempotency_key="execute-stale-1",
                request_hash="execute-stale-hash",
                input_payload={"message": "我要退票"},
            )
            action = repository.upsert_proposed_action(
                session_id=int(assistant_session["id"]),
                run_id=int(run["id"]),
                task_id=None,
                action_key="execute-stale:submit_refund:TK-300",
                action_type="submit_refund",
                title="提交退票申请",
                payload={"orderNo": "TK-300"},
            )
            repository.update_proposed_action_status(int(action["id"]), "CONFIRMED")
            executor = _CountingActionExecutor()
            service = CustomerAssistantService(repository, action_executor_registry=executor)

            with self.assertRaises(BizError) as error:
                service.execute_action(int(action["id"]))

            current = repository.get_proposed_action(int(action["id"]))

        self.assertEqual(executor.calls, 0)
        self.assertIn("Only confirmed proposed actions can be executed", str(error.exception))
        self.assertEqual(current["status"], "CONFIRMED")


class _StaleClaimRepository(CustomerAssistantRepository):
    def transition_proposed_action_status(
        self,
        action_id: int,
        *,
        expected_status: str,
        next_status: str,
        result: dict | None = None,
    ) -> dict | None:
        return None


class _CountingActionExecutor(MockActionExecutorRegistry):
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, action_type: str, payload: dict) -> MockActionExecutionResult:
        self.calls += 1
        return super().execute(action_type, payload)


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session("customer_assistant_execution", tables=customer_assistant_tables(), register=register_customer_assistant_tables) as session:
        yield session


if __name__ == "__main__":
    unittest.main()
