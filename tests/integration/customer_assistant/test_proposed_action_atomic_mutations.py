from contextlib import contextmanager
import unittest
from collections.abc import Iterator
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import BizError
from app.modules.customer_assistant.domain.service import CustomerAssistantService
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository
from app.modules.customer_assistant.infra.schema import customer_assistant_tables, register_customer_assistant_tables
from tests.support.mysql import mysql8_session


class CustomerAssistantProposedActionAtomicMutationTest(unittest.TestCase):
    def test_confirm_reject_and_modify_fail_without_events_when_pending_claim_is_stale(self) -> None:
        with _session() as session:
            repository = _StalePendingMutationRepository(session)
            confirm_id = _create_action(repository, "confirm")
            reject_id = _create_action(repository, "reject")
            modify_id = _create_action(repository, "modify")
            task_control_id, task_id = _create_task_control_action(repository, "cancel")
            service = CustomerAssistantService(repository)

            with self.assertRaises(BizError):
                service.confirm_action(confirm_id)
            with self.assertRaises(BizError):
                service.reject_action(reject_id)
            with self.assertRaises(BizError):
                service.update_action(modify_id, title="新的标题")
            with self.assertRaises(BizError):
                service.confirm_action(task_control_id)

            confirm = repository.get_proposed_action(confirm_id)
            reject = repository.get_proposed_action(reject_id)
            modify = repository.get_proposed_action(modify_id)
            task_control = repository.get_proposed_action(task_control_id)
            task = repository.get_task(task_id)

        self.assertEqual(confirm["status"], "PENDING")
        self.assertEqual(reject["status"], "PENDING")
        self.assertEqual(modify["status"], "PENDING")
        self.assertEqual(task_control["status"], "PENDING")
        self.assertEqual(task["status"], "RUNNING")
        self.assertEqual(repository.appended_event_types, [])


class _StalePendingMutationRepository(CustomerAssistantRepository):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.appended_event_types: list[str] = []

    def transition_proposed_action_status(
        self,
        action_id: int,
        *,
        expected_status: str,
        next_status: str,
        result: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        del action_id, expected_status, next_status, result
        return None

    def update_pending_proposed_action(
        self,
        action_id: int,
        *,
        title: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        del action_id, title, payload
        return None

    def append_event(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self.appended_event_types.append(str(args[1] if len(args) > 1 else kwargs.get("event_type")))
        return super().append_event(*args, **kwargs)


def _create_action(repository: CustomerAssistantRepository, suffix: str) -> int:
    assistant_session = repository.create_session({"case": f"atomic-{suffix}"})
    session_id = int(assistant_session["id"])
    run, _ = repository.create_run(
        session_id,
        idempotency_key=f"atomic-{suffix}",
        request_hash=f"atomic-{suffix}",
        input_payload={"source": "atomic-test"},
    )
    action = repository.upsert_proposed_action(
        session_id=session_id,
        run_id=int(run["id"]),
        task_id=None,
        action_key=f"atomic:{suffix}:submit_refund",
        action_type="submit_refund",
        title="提交退票申请",
        payload={"orderNo": f"TK-{suffix}"},
    )
    return int(action["id"])


def _create_task_control_action(repository: CustomerAssistantRepository, suffix: str) -> tuple[int, int]:
    assistant_session = repository.create_session({"case": f"atomic-task-command-{suffix}"})
    session_id = int(assistant_session["id"])
    run, _ = repository.create_run(
        session_id,
        idempotency_key=f"atomic-task-command-{suffix}",
        request_hash=f"atomic-task-command-{suffix}",
        input_payload={"source": "atomic-test"},
    )
    task = repository.upsert_task(
        session_id,
        "refund_ticket:TK-task-control",
        "REFUND",
        "TK-task-control",
        "chatflow_sop",
        "refund_ticket",
        status="RUNNING",
    )
    action = repository.upsert_proposed_action(
        session_id=session_id,
        run_id=int(run["id"]),
        task_id=int(task["id"]),
        action_key=f"atomic-task-command:{suffix}:cancel",
        action_type="PROPOSED_TASK_COMMAND",
        title="取消任务：refund_ticket:TK-task-control",
        payload={
            "turnMode": "operator_apply_task_command",
            "requiresConfirmation": True,
            "controlType": "cancel",
            "reason": "stale cancel should not apply",
            "taskCommand": {
                "type": "CANCEL_TASK",
                "taskKey": "refund_ticket:TK-task-control",
                "taskType": "REFUND",
                "businessKey": "TK-task-control",
                "workerType": "chatflow_sop",
                "workerRef": "refund_ticket",
                "reason": "stale cancel should not apply",
            },
        },
    )
    return int(action["id"]), int(task["id"])


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session(
        "customer_assistant_action_atomic_mutations",
        tables=customer_assistant_tables(),
        register=register_customer_assistant_tables,
    ) as session:
        yield session


if __name__ == "__main__":
    unittest.main()
