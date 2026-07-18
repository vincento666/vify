import asyncio
import json
import queue
import threading
import time
import unittest
from collections.abc import Generator
from datetime import datetime
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import Base, get_session
from app.core.db_write import insert_and_get_id
from app.core.schema import register_baseline_tables
from app.main import app
from app.modules.customer_assistant.infra.schema import register_customer_assistant_tables
from app.modules.runtime.infra.runtime_job_repository import RuntimeJobRepository
from app.modules.workflow.runtime_job_worker import build_runtime_job_worker
from tests.support.mysql import mysql8_unittest_database


class CustomerAssistantChatflowSopLiveStreamE2eTest(unittest.TestCase):
    def setUp(self) -> None:
        self._database = mysql8_unittest_database(
            self,
            "customer_assistant_chatflow_live_stream",
            register=_register_all_tables,
        )
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        self._settings = Settings(
            runtime_lab_sop_chatflow_ids=None,
            customer_assistant_worker_wait_deadline_seconds=0.2,
            customer_assistant_worker_timeout_seconds=5.0,
            customer_assistant_sop_llm_mode="live",
        )
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: self._settings

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_sse_keeps_chatflow_refs_while_live_provider_stream_is_cancelled(self) -> None:
        fake_client = _CancellableAsyncProviderClient()
        received: queue.Queue[dict[str, Any]] = queue.Queue()

        with (
            patch("app.modules.workflow.domain.service.ProviderBackedOpenAIChatClient", lambda _config: fake_client),
            TestClient(app) as stream_client,
            TestClient(app) as client,
        ):
            model_config_id = _seed_live_model_config(self._factory)
            chatflow = _create_llm_chatflow(client, model_config_id)
            self._settings = self._settings.model_copy(
                update={"runtime_lab_sop_chatflow_ids": f"refund_ticket:{chatflow['id']}"}
            )
            session_id = client.post("/api/v1/customer-assistant/sessions", json={}).json()["data"]["id"]
            stream_thread = threading.Thread(
                target=_collect_customer_assistant_events,
                args=(stream_client, session_id, received),
                daemon=True,
            )
            stream_thread.start()

            turn = client.post(
                f"/api/v1/customer-assistant/sessions/{session_id}/turns",
                json={"message": "我要退票", "idempotencyKey": "chatflow-live-stream"},
            )
            self.assertEqual(turn.status_code, 200, turn.text)
            refs = _wait_for_runtime_refs(client, int(session_id))
            outer_events = _drain_until(received, "worker_result_received")

            worker_result: dict[str, Any] = {}

            def drain_job() -> None:
                with self._factory() as session:
                    job = RuntimeJobRepository(session).get_by_run(int(refs["runId"]))
                    assert job is not None
                    worker_result.update(
                        build_runtime_job_worker(
                            session,
                            owner="chatflow",
                            worker_id=f"customer-assistant-live-stream-{refs['runId']}",
                        ).run_once(job_id=int(job["id"]))
                    )

            worker_thread = threading.Thread(target=drain_job, daemon=True)
            worker_thread.start()
            self.assertTrue(fake_client.first_delta_sent.wait(timeout=3), "shared async provider did not stream")
            cancelled = client.post(f"/api/v1/runtime-runs/{refs['runId']}/cancel")
            self.assertEqual(cancelled.status_code, 200, cancelled.text)
            self.assertEqual(cancelled.json()["data"]["status"], "CANCELLED")
            self.assertTrue(fake_client.cancelled.wait(timeout=1), "cancel did not close provider stream")
            worker_thread.join(timeout=3)
            child_result = client.get(str(refs["resultRef"])).json()["data"]
            child_events = client.get(str(refs["eventsRef"])).json()["data"]["list"]

        self.assertFalse(worker_thread.is_alive(), "Chatflow runtime job did not return after cancellation")
        self.assertEqual(worker_result["status"], "CANCELLED")
        self.assertEqual(child_result["status"], "CANCELLED")
        self.assertEqual(fake_client.async_stream_calls, 1)
        self.assertTrue(fake_client.closed.is_set())
        self.assertIn("worker_started", [event["type"] for event in outer_events])
        self.assertIn("worker_result_received", [event["type"] for event in outer_events])
        self.assertEqual([event["type"] for event in child_events].count("llm_delta"), 1)
        self.assertIn("workflow_run_cancelled", [event["type"] for event in child_events])
        self.assertNotIn("workflow_node_completed", [event["type"] for event in child_events])

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session


def _register_all_tables() -> None:
    register_baseline_tables()
    register_customer_assistant_tables()


def _seed_live_model_config(factory: Any) -> int:
    now = datetime.now()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    with factory() as session:
        provider_id = insert_and_get_id(
            session,
            provider,
            {
                "name": f"Customer Assistant Live Stream Provider {time.time_ns()}",
                "type": "OPENAI",
                "base_url": "https://customer-assistant-live-stream.example.test/v1",
                "auth_config": {"api_key": "sk-customer-assistant-live-stream"},
                "description": "",
                "enabled": True,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        model_config_id = insert_and_get_id(
            session,
            model_config,
            {
                "provider_id": provider_id,
                "name": "customer-assistant-live-stream-model",
                "model_id": "customer-assistant-live-stream-model",
                "context_size": 2048,
                "extra_params": {},
                "enabled": True,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        session.commit()
    return int(model_config_id)


def _create_llm_chatflow(client: TestClient, model_config_id: int) -> dict[str, Any]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Customer Assistant Live Stream SOP {time.time_ns()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "llm",
                    "type": "LLM",
                    "name": "Provider LLM",
                    "config": {
                        "prompt": "Customer Assistant SSE: {{sys.query}}",
                        "outputVariable": "answer",
                        "modelConfigId": model_config_id,
                    },
                },
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final", "output": "{{llm.answer}}"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "llm", "condition": None},
                {"sourceNodeKey": "llm", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _collect_customer_assistant_events(
    client: TestClient,
    session_id: int,
    event_queue: queue.Queue[dict[str, Any]],
) -> None:
    with client.stream(
        "GET",
        f"/api/v1/customer-assistant/sessions/{session_id}/events/stream?afterSequence=0&heartbeatMs=100&_testLimit=10",
    ) as response:
        if response.status_code != 200:
            event_queue.put({"type": "_stream_error", "status": response.status_code})
            return
        for line in response.iter_lines():
            if line.startswith("data: "):
                event_queue.put(json.loads(line.removeprefix("data: ")))


def _wait_for_runtime_refs(client: TestClient, session_id: int, timeout: float = 3.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    latest: list[dict[str, Any]] = []
    while time.monotonic() < deadline:
        latest = client.get(f"/api/v1/customer-assistant/sessions/{session_id}/tasks").json()["data"]["list"]
        for task in latest:
            evidence = task.get("lastResult", {}).get("evidence", {})
            refs = evidence.get("runtimeRefs") if isinstance(evidence, dict) else None
            if isinstance(refs, dict) and refs.get("runId"):
                return refs
        time.sleep(0.05)
    raise AssertionError(f"Timed out waiting for Chatflow runtime refs: {latest}")


def _drain_until(event_queue: queue.Queue[dict[str, Any]], wanted_type: str, timeout: float = 3.0) -> list[dict[str, Any]]:
    deadline = time.monotonic() + timeout
    events: list[dict[str, Any]] = []
    while time.monotonic() < deadline:
        try:
            event = event_queue.get(timeout=0.05)
        except queue.Empty:
            continue
        events.append(event)
        if event.get("type") == wanted_type:
            return events
    raise AssertionError(f"Timed out waiting for {wanted_type}: {events}")


class _CancellableAsyncProviderClient:
    def __init__(self) -> None:
        self.first_delta_sent = threading.Event()
        self.cancelled = threading.Event()
        self.closed = threading.Event()
        self.async_stream_calls = 0

    async def stream_complete_async(self, _payload: dict[str, Any], on_delta: Any = None) -> dict[str, Any]:
        self.async_stream_calls += 1
        if on_delta is not None:
            on_delta("first ")
        self.first_delta_sent.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled.set()
            raise
        finally:
            self.closed.set()
        return {"choices": [{"message": {"content": "unexpected"}}]}


if __name__ == "__main__":
    unittest.main()
