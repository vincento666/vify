import json
import queue
import tempfile
import threading
import time
import unittest
from collections.abc import Generator
from pathlib import Path

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import Base, get_session
from app.main import app
from app.modules.customer_assistant.domain.models import TaskItem, TaskStatus, WorkerResult
from app.modules.customer_assistant.domain.scheduler import LocalWorkerScheduler
from app.modules.customer_assistant.domain.service import CustomerAssistantService
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository
from app.modules.customer_assistant.infra.schema import (
    customer_assistant_tables,
    register_customer_assistant_tables,
)
from app.modules.customer_assistant.web.router import get_customer_assistant_service


class CustomerAssistantSseStreamingE2eTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmp_dir.name) / "customer_assistant_sse.db"
        self._engine = create_engine(
            f"sqlite:///{db_path}",
            future=True,
            connect_args={"check_same_thread": False},
        )
        register_customer_assistant_tables()
        Base.metadata.create_all(bind=self._engine, tables=customer_assistant_tables())
        self._factory = sessionmaker(bind=self._engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self._worker = _BlockingWorker()
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(runtime_lab_sop_chatflow_ids=None)
        app.dependency_overrides[get_customer_assistant_service] = self._service_override

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_customer_assistant_service, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_sse_receives_worker_started_before_turn_response_completes(self) -> None:
        event_queue: queue.Queue[dict[str, object]] = queue.Queue()
        post_done = threading.Event()
        post_response: dict[str, object] = {}

        with TestClient(app) as stream_client, TestClient(app) as post_client:
            created = post_client.post("/api/v1/customer-assistant/sessions", json={})
            session_id = created.json()["data"]["id"]

            stream_thread = threading.Thread(
                target=_collect_stream_events,
                args=(stream_client, session_id, event_queue),
                daemon=True,
            )
            stream_thread.start()

            post_thread = threading.Thread(
                target=_post_turn,
                args=(post_client, session_id, post_done, post_response),
                daemon=True,
            )
            post_thread.start()

            received = _drain_until(event_queue, "worker_started", timeout=5)
            self.assertIn("run_started", [event["type"] for event in received])
            self.assertIn("worker_started", [event["type"] for event in received])
            self.assertFalse(post_done.is_set(), "turn response completed before worker_started reached SSE")

            self._worker.release.set()
            post_thread.join(timeout=5)
            stream_thread.join(timeout=5)

        self.assertTrue(post_done.is_set())
        self.assertEqual(post_response["status_code"], 200)

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session

    def _service_override(self, session: Session = Depends(get_session)) -> CustomerAssistantService:
        return CustomerAssistantService(
            CustomerAssistantRepository(session),
            scheduler=LocalWorkerScheduler({"chatflow_sop": self._worker}),
        )


class _BlockingWorker:
    def __init__(self) -> None:
        self.release = threading.Event()

    def run(self, task: TaskItem, message: str) -> WorkerResult:
        if not self.release.wait(timeout=5):
            raise TimeoutError("blocking worker was not released")
        return WorkerResult(
            task_id=int(task.id or 0),
            worker_type=task.worker_type,
            status=TaskStatus.WAITING,
            customer_reply_draft=f"waiting on {message}",
            missing_fields=["order_no"],
        )


def _collect_stream_events(
    client: TestClient,
    session_id: int,
    event_queue: queue.Queue[dict[str, object]],
) -> None:
    with client.stream(
        "GET",
        f"/api/v1/customer-assistant/sessions/{session_id}/events/stream"
        "?afterSequence=0&heartbeatMs=100&_testLimit=6",
    ) as response:
        for line in response.iter_lines():
            if line.startswith("data: "):
                event_queue.put(json.loads(line.removeprefix("data: ")))


def _post_turn(
    client: TestClient,
    session_id: int,
    post_done: threading.Event,
    post_response: dict[str, object],
) -> None:
    response = client.post(
        f"/api/v1/customer-assistant/sessions/{session_id}/turns",
        json={"message": "我要退票", "idempotencyKey": "stream-live"},
    )
    post_response["status_code"] = response.status_code
    post_done.set()


def _drain_until(
    event_queue: queue.Queue[dict[str, object]],
    wanted_type: str,
    timeout: float,
) -> list[dict[str, object]]:
    deadline = time.monotonic() + timeout
    received: list[dict[str, object]] = []
    while time.monotonic() < deadline:
        try:
            event = event_queue.get(timeout=0.1)
        except queue.Empty:
            continue
        received.append(event)
        if event.get("type") == wanted_type:
            return received
    raise AssertionError(f"Timed out waiting for {wanted_type}; got {[event.get('type') for event in received]}")


if __name__ == "__main__":
    unittest.main()
