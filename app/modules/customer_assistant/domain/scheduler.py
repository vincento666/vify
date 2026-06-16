from concurrent.futures import ThreadPoolExecutor, TimeoutError

from app.modules.customer_assistant.domain.models import TaskItem, WorkerResult
from app.modules.customer_assistant.domain.worker import TaskWorker
from app.modules.customer_assistant.domain.models import TaskStatus


class LocalWorkerScheduler:
    def __init__(self, workers: dict[str, TaskWorker], task_timeout_seconds: float = 5.0) -> None:
        self._workers = workers
        self._task_timeout_seconds = task_timeout_seconds

    def run(self, tasks: list[TaskItem], message: str) -> list[WorkerResult]:
        if not tasks:
            return []
        results: list[WorkerResult] = []
        executor = ThreadPoolExecutor(max_workers=max(1, len(tasks)))
        try:
            future_by_task = {
                executor.submit(self._run_one, task, message): task
                for task in tasks
            }
            for future, task in future_by_task.items():
                try:
                    results.append(future.result(timeout=self._task_timeout_seconds))
                except TimeoutError:
                    future.cancel()
                    results.append(self._timeout_result(task))
                except Exception as exc:
                    results.append(self._failed_result(task, str(exc)))
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
        return sorted(results, key=lambda result: result.task_id)

    def _run_one(self, task: TaskItem, message: str) -> WorkerResult:
        worker = self._workers.get(task.worker_type)
        if worker is None:
            raise KeyError(f"No worker registered for type: {task.worker_type}")
        return worker.run(task, message)

    @staticmethod
    def _failed_result(task: TaskItem, message: str) -> WorkerResult:
        return WorkerResult(
            task_id=int(task.id or 0),
            worker_type=task.worker_type,
            status=TaskStatus.FAILED,
            error={"code": "WORKER_FAILED", "message": message},
        )

    @staticmethod
    def _timeout_result(task: TaskItem) -> WorkerResult:
        return WorkerResult(
            task_id=int(task.id or 0),
            worker_type=task.worker_type,
            status=TaskStatus.FAILED,
            events=[
                {
                    "type": "worker_timeout_started",
                    "source": "customer_assistant_worker",
                    "payload": {"taskId": task.id, "workerType": task.worker_type},
                },
                {
                    "type": "worker_timed_out",
                    "source": "customer_assistant_worker",
                    "payload": {"taskId": task.id, "workerType": task.worker_type},
                },
            ],
            error={"code": "WORKER_TIMEOUT", "message": "worker timed out"},
        )
