import re

from app.modules.customer_assistant.domain.models import TaskCommand, TaskCommandType, TaskLedger, TaskStatus


class DeterministicTaskRecognitionController:
    def recognize(self, message: str, ledger: TaskLedger) -> list[TaskCommand]:
        text = message.strip().lower()
        commands: list[TaskCommand] = []

        if _is_cancel(text):
            for task in ledger.active_tasks():
                if _mentions_task(text, task.task_key) or not _mentions_any_task(text):
                    commands.append(TaskCommand(TaskCommandType.CANCEL_TASK, task_key=task.task_key, reason="cancel"))
            if commands:
                return commands

        if _has_refund_intent(text) or _continues_refund(text, ledger):
            commands.append(self._task_command("refund_ticket", ledger))

        if _has_baggage_intent(text):
            commands.append(
                self._task_command(
                    "baggage_qa",
                    ledger,
                    task_type="QA",
                    worker_type="stub_qa",
                    worker_ref="baggage_allowance",
                )
            )

        return commands

    def _task_command(
        self,
        task_key: str,
        ledger: TaskLedger,
        *,
        task_type: str = "REFUND",
        worker_type: str = "chatflow_sop",
        worker_ref: str = "refund_ticket",
    ) -> TaskCommand:
        existing = ledger.by_key(task_key)
        command_type = TaskCommandType.ADD_TASK
        if existing is not None and existing.status not in {TaskStatus.COMPLETED, TaskStatus.CANCELLED}:
            command_type = TaskCommandType.RETAIN_TASK
        return TaskCommand(
            type=command_type,
            task_key=task_key,
            task_type=task_type,
            business_key=task_key,
            worker_type=worker_type,
            worker_ref=worker_ref,
            reason="deterministic_intent",
        )


def _has_refund_intent(text: str) -> bool:
    return any(term in text for term in ("退票", "退款", "退机票", "取消行程", "refund"))


def _has_baggage_intent(text: str) -> bool:
    return any(term in text for term in ("行李", "托运", "baggage", "allowance"))


def _is_cancel(text: str) -> bool:
    return any(term in text for term in ("取消", "不用", "撤销", "cancel"))


def _continues_refund(text: str, ledger: TaskLedger) -> bool:
    refund = ledger.by_key("refund_ticket")
    if refund is None or refund.status not in {TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.WAITING}:
        return False
    if any(term in text for term in ("确认", "提交", "继续", "是的", "可以")):
        return True
    return bool(re.search(r"(订单号|订单|order|tk|pnr|[a-z]{1,4}[-_]?\d{3,20})", text, re.IGNORECASE))


def _mentions_task(text: str, task_key: str) -> bool:
    if task_key == "refund_ticket":
        return _has_refund_intent(text)
    if task_key == "baggage_qa":
        return _has_baggage_intent(text)
    return task_key.lower() in text


def _mentions_any_task(text: str) -> bool:
    return _has_refund_intent(text) or _has_baggage_intent(text)
