from typing import Protocol

from app.modules.customer_assistant.domain.models import TaskItem, WorkerResult


class TaskWorker(Protocol):
    def run(self, task: TaskItem, message: str) -> WorkerResult:
        ...
