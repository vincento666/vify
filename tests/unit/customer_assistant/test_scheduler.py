import time
import unittest

from app.modules.customer_assistant.domain.models import TaskItem, TaskStatus, WorkerResult
from app.modules.customer_assistant.domain.scheduler import LocalWorkerScheduler


class LocalWorkerSchedulerTest(unittest.TestCase):
    def test_fanout_join_keeps_other_task_success_when_one_worker_fails(self) -> None:
        scheduler = LocalWorkerScheduler(
            workers={
                "ok": _OkWorker(),
                "boom": _FailingWorker(),
            }
        )
        ok_task = _task(2, "baggage_qa", "ok")
        failing_task = _task(1, "refund_ticket", "boom")

        results = scheduler.run([ok_task, failing_task], message="我要退票，也想问行李额")

        self.assertEqual([result.task_id for result in results], [1, 2])
        self.assertEqual([result.status for result in results], [TaskStatus.FAILED, TaskStatus.COMPLETED])
        self.assertEqual(results[0].error["message"], "worker exploded")
        self.assertEqual(results[1].customer_reply_draft, "ok draft")

    def test_timeout_returns_without_waiting_for_blocked_worker_and_emits_events(self) -> None:
        scheduler = LocalWorkerScheduler(
            workers={"blocked": _BlockedWorker()},
            task_timeout_seconds=0.01,
        )
        task = _task(1, "refund_ticket", "blocked")

        started = time.perf_counter()
        results = scheduler.run([task], message="我要退票")
        elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 0.15)
        self.assertEqual(results[0].status, TaskStatus.FAILED)
        self.assertEqual(
            [event["type"] for event in results[0].events],
            ["worker_timeout_started", "worker_timed_out"],
        )


class _OkWorker:
    def run(self, task: TaskItem, message: str) -> WorkerResult:
        return WorkerResult(
            task_id=int(task.id or 0),
            worker_type=task.worker_type,
            status=TaskStatus.COMPLETED,
            operator_recommendation=f"ok {message}",
            customer_reply_draft="ok draft",
        )


class _FailingWorker:
    def run(self, task: TaskItem, message: str) -> WorkerResult:
        raise RuntimeError("worker exploded")


class _BlockedWorker:
    def run(self, task: TaskItem, message: str) -> WorkerResult:
        time.sleep(0.25)
        return WorkerResult(
            task_id=int(task.id or 0),
            worker_type=task.worker_type,
            status=TaskStatus.COMPLETED,
        )


def _task(task_id: int, task_key: str, worker_type: str) -> TaskItem:
    return TaskItem(
        id=task_id,
        session_id=10,
        task_key=task_key,
        task_type="QA",
        business_key=task_key,
        short_id=task_key[:4].upper(),
        status=TaskStatus.PENDING,
        worker_type=worker_type,
        worker_ref=task_key,
    )


if __name__ == "__main__":
    unittest.main()
