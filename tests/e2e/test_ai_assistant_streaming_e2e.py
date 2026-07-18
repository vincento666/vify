import json
import threading
import unittest
from collections.abc import Generator
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
from app.modules.ai_assistant.domain.live_model import LivePlannerConfig, QwenLivePlanner
from app.modules.ai_assistant.domain.tools import RiskLevel, ToolManifest, ToolRegistry, ToolResult
from app.modules.ai_assistant.infra.repository import AiAssistantRepository
from app.modules.ai_assistant.web.router import get_ai_assistant_service
from app.modules.chat.domain.llm_request import FakeOpenAIChatClient
from tests.support.mysql import mysql8_unittest_database


class AiAssistantStreamingE2ETest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_streaming_e2e",
            tables=ai_assistant_tables(),
            register=register_ai_assistant_tables,
        )
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        self._fake_client = FakeDeltaChatClient(
            streamed_chunks=["实时", "输出"],
            response_payload={
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "实时输出"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
            },
        )
        self._tool_registry: ToolRegistry | None = None
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)
        app.dependency_overrides[get_ai_assistant_service] = self._service_override

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_ai_assistant_service, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_async_run_streams_text_delta_and_recovers_from_snapshot_and_cursor(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/ai-assistant/sessions", json={"title": "Streaming E2E"})
            session_id = created.json()["data"]["id"]
            started = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json={
                    "message": "请实时输出",
                    "idempotencyKey": "streaming-e2e-async",
                    "modelMode": "live",
                    "approvalMode": "smart_approval",
                },
            )
            payload = started.json()["data"]
            run_id = int(payload["runId"])
            self._process_run(run_id)
            with client.stream("GET", f"{payload['eventStreamRef']}&_testLimit=10") as stream_response:
                streamed = _read_sse_frames(stream_response, 10)
            snapshot = client.get(f"/api/v1/ai-assistant/runs/{run_id}/snapshot")
            first_delta_sequence = next(frame["data"]["sequence"] for frame in streamed if frame["data"]["type"] == "text.delta")
            with client.stream(
                "GET",
                f"/api/v1/ai-assistant/runs/{run_id}/events/stream?_testLimit=1",
                headers={"Last-Event-ID": str(first_delta_sequence)},
            ) as resumed_response:
                resumed = _read_sse_frames(resumed_response, 1)

        self.assertEqual(started.status_code, 200, started.text)
        self.assertIn("/events/stream?afterSequence=0", payload["eventStreamRef"])
        self.assertEqual([frame["data"]["payload"].get("delta") for frame in streamed if frame["data"]["type"] == "text.delta"], ["实时", "输出"])
        self.assertEqual(snapshot.status_code, 200, snapshot.text)
        self.assertGreaterEqual(snapshot.json()["data"]["streamCursor"]["lastSequence"], streamed[-1]["data"]["sequence"])
        self.assertGreater(resumed[0]["data"]["sequence"], first_delta_sequence)

    def test_cancelled_worker_run_does_not_overwrite_terminal_control_with_completion(self) -> None:
        blocking_client = BlockingDeltaChatClient(
            streamed_chunks=["首段", "尾段"],
            response_payload={
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "首段尾段"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
            },
        )
        self._fake_client = blocking_client
        worker_errors: list[BaseException] = []

        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Cancel worker"}).json()["data"][
                "id"
            ]
            started = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json={
                    "message": "请实时输出后等待取消",
                    "idempotencyKey": "streaming-e2e-cancel-running",
                    "modelMode": "live",
                    "approvalMode": "smart_approval",
                },
            ).json()["data"]
            worker = threading.Thread(
                target=lambda: self._process_run_capturing_errors(started["runId"], worker_errors),
                daemon=True,
            )
            worker.start()
            self.assertTrue(blocking_client.first_delta_sent.wait(timeout=5), "worker did not emit first delta")
            cancelled = client.post(f"/api/v1/ai-assistant/runs/{started['runId']}/cancel", json={"actorId": "operator"})
            running_snapshot = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/snapshot").json()["data"]
            blocking_client.release_completion.set()
            worker.join(timeout=5)
            final_snapshot = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/snapshot").json()["data"]
            events = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/events").json()["data"]["list"]

        self.assertEqual(cancelled.status_code, 200, cancelled.text)
        self.assertEqual(running_snapshot["run"]["status"], "CANCELLED")
        self.assertFalse(worker.is_alive(), "worker did not stop after cancellation was released")
        self.assertEqual(worker_errors, [])
        self.assertEqual(final_snapshot["run"]["status"], "CANCELLED")
        event_types = [event["type"] for event in events]
        self.assertIn("run.cancelled", event_types)
        self.assertNotIn("run.completed", event_types)

    def test_worker_started_run_records_text_delta_before_terminal_completion(self) -> None:
        blocking_client = BlockingDeltaChatClient(
            streamed_chunks=["活跃", "完成"],
            response_payload={
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "活跃完成"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
            },
        )
        self._fake_client = blocking_client
        worker_errors: list[BaseException] = []

        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Active stream"}).json()["data"][
                "id"
            ]
            started = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json={
                    "message": "请实时输出并保持运行",
                    "idempotencyKey": "streaming-e2e-active-delta",
                    "modelMode": "live",
                    "approvalMode": "smart_approval",
                },
            ).json()["data"]
            worker = threading.Thread(
                target=lambda: self._process_run_capturing_errors(started["runId"], worker_errors),
                daemon=True,
            )
            worker.start()
            self.assertTrue(blocking_client.first_delta_sent.wait(timeout=5), "worker did not emit first delta")
            events = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/events").json()["data"]["list"]
            first_delta = next(event for event in events if event["type"] == "text.delta")
            running_snapshot = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/snapshot").json()["data"]
            blocking_client.release_completion.set()
            worker.join(timeout=5)
            final_snapshot = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/snapshot").json()["data"]

        self.assertEqual(first_delta["payload"]["delta"], "活跃")
        self.assertEqual(running_snapshot["run"]["status"], "RUNNING")
        self.assertFalse(worker.is_alive(), "worker did not finish after release")
        self.assertEqual(worker_errors, [])
        self.assertEqual(final_snapshot["run"]["status"], "COMPLETED")

    def test_async_live_queue_persists_safe_model_ref_without_raw_api_key(self) -> None:
        self._fake_client = FakeDeltaChatClient(
            streamed_chunks=["配置", "生效"],
            response_payload={
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "配置生效"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
            },
        )

        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Worker config"}).json()["data"][
                "id"
            ]
            started = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json={
                    "message": "请使用 worker 传入的模型配置",
                    "idempotencyKey": "streaming-e2e-worker-model-config",
                    "modelMode": "live",
                    "approvalMode": "smart_approval",
                    "modelConfig": {
                        "provider": "openrouter",
                        "baseUrl": "https://openrouter.ai/api/v1",
                        "model": "qwen/start-safe-config",
                        "apiKey": "sk-start-temp",
                        "temperature": 0,
                        "maxTokens": 128,
                    },
                },
            ).json()["data"]
            snapshot = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/snapshot").json()["data"]

        self.assertEqual(started["executionMode"], "durable_worker")
        self.assertIn("/api/v1/runtime-jobs/", started["runtimeJobRef"])
        self.assertEqual(snapshot["run"]["status"], "QUEUED")
        runtime_request = snapshot["checkpoint"]["request"]
        self.assertEqual(runtime_request["modelConfig"]["model"], "qwen/start-safe-config")
        self.assertTrue(runtime_request["modelConfig"]["hasApiKey"])
        self.assertNotIn("apiKey", runtime_request["modelConfig"])

    def test_deprecated_worker_shim_ignores_divergent_request_model_config(self) -> None:
        self._fake_client = FakeDeltaChatClient(
            streamed_chunks=["不应", "执行"],
            response_payload={
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "不应执行"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
            },
        )

        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Worker drift"}).json()["data"][
                "id"
            ]
            started = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json={
                    "message": "worker 请求不能改变排队时的执行模型",
                    "idempotencyKey": "streaming-e2e-worker-model-config-drift",
                    "modelMode": "deterministic",
                    "approvalMode": "smart_approval",
                    "modelConfig": {
                        "provider": "openrouter",
                        "baseUrl": "https://openrouter.ai/api/v1",
                        "model": "qwen/queued-config",
                        "apiKey": "sk-queued-temp",
                        "temperature": 0,
                        "maxTokens": 128,
                    },
                },
            ).json()["data"]
            compatibility = client.post(
                f"/api/v1/ai-assistant/runs/{started['runId']}/worker/process",
                json={
                    "modelConfig": {
                        "provider": "openrouter",
                        "baseUrl": "https://openrouter.ai/api/v1",
                        "model": "qwen/divergent-worker-config",
                        "apiKey": "sk-worker-temp",
                        "temperature": 0,
                        "maxTokens": 128,
                    }
                },
            )
            queued_snapshot = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/snapshot").json()["data"]
            self._process_run(started["runId"])
            snapshot = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/snapshot").json()["data"]
            events = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/events").json()["data"]["list"]

        self.assertEqual(compatibility.status_code, 200, compatibility.text)
        self.assertTrue(compatibility.json()["data"]["deprecation"]["deprecated"])
        self.assertTrue(compatibility.json()["data"]["deprecation"]["requestPayloadIgnored"])
        self.assertEqual(queued_snapshot["run"]["status"], "QUEUED")
        self.assertEqual(self._fake_client.captured_payloads, [])
        self.assertEqual(snapshot["run"]["status"], "COMPLETED")
        self.assertIn("run.worker_started", [event["type"] for event in events])
        self.assertEqual(
            snapshot["checkpoint"]["request"]["modelConfig"]["model"],
            "qwen/queued-config",
        )

    def test_cancelled_deterministic_tool_run_does_not_overwrite_terminal_control_with_completion(self) -> None:
        tool_started = threading.Event()
        release_tool = threading.Event()
        worker_errors: list[BaseException] = []

        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Cancel deterministic"}).json()[
                "data"
            ]["id"]
            started = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json={
                    "message": "阻塞工具后取消",
                    "idempotencyKey": "streaming-e2e-cancel-deterministic-tool",
                    "modelMode": "deterministic",
                    "approvalMode": "smart_approval",
                    "toolName": "blocking_echo",
                    "toolInput": {"message": "阻塞工具后取消"},
                },
            ).json()["data"]
            worker = threading.Thread(
                target=lambda: self._process_run_with_registry(
                    started["runId"],
                    worker_errors,
                    _blocking_tool_registry(tool_started=tool_started, release_tool=release_tool),
                ),
                daemon=True,
            )
            worker.start()
            self.assertTrue(tool_started.wait(timeout=5), "deterministic tool did not start")
            cancelled = client.post(f"/api/v1/ai-assistant/runs/{started['runId']}/cancel", json={"actorId": "uat"})
            cancelled_snapshot = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/snapshot").json()["data"]
            release_tool.set()
            worker.join(timeout=5)
            final_snapshot = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/snapshot").json()["data"]
            events = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/events").json()["data"]["list"]

        self.assertEqual(cancelled.status_code, 200, cancelled.text)
        self.assertEqual(cancelled_snapshot["run"]["status"], "CANCELLED")
        self.assertFalse(worker.is_alive(), "worker did not finish after deterministic tool release")
        self.assertEqual(worker_errors, [])
        self.assertEqual(final_snapshot["run"]["status"], "CANCELLED")
        event_types = [event["type"] for event in events]
        self.assertIn("run.cancelled", event_types)
        self.assertNotIn("run.completed", event_types)

    def test_cancelled_deterministic_no_tool_run_does_not_emit_completion(self) -> None:
        step_completed = threading.Event()
        release_worker = threading.Event()
        worker_errors: list[BaseException] = []
        original_append_event = AiAssistantRepository.append_event

        def blocking_append_event(repository, *args, **kwargs):
            event = original_append_event(repository, *args, **kwargs)
            if kwargs.get("event_type") == "plan.step_completed":
                step_completed.set()
                release_worker.wait(timeout=5)
            return event

        with patch.object(
            AiAssistantRepository,
            "append_event",
            new=blocking_append_event,
        ):
            with TestClient(app) as client:
                session_id = client.post(
                    "/api/v1/ai-assistant/sessions",
                    json={"title": "Cancel deterministic no tool"},
                ).json()["data"]["id"]
                started = client.post(
                    f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                    json={
                        "message": "无工具回复完成前取消",
                        "idempotencyKey": "streaming-e2e-cancel-deterministic-no-tool",
                        "modelMode": "deterministic",
                        "approvalMode": "smart_approval",
                    },
                ).json()["data"]
                worker = threading.Thread(
                    target=lambda: self._process_run_capturing_errors(
                        started["runId"],
                        worker_errors,
                    ),
                    daemon=True,
                )
                worker.start()
                self.assertTrue(
                    step_completed.wait(timeout=5),
                    "deterministic no-tool run did not complete its plan step",
                )
                cancelled = client.post(
                    f"/api/v1/ai-assistant/runs/{started['runId']}/cancel",
                    json={"actorId": "uat"},
                )
                release_worker.set()
                worker.join(timeout=5)
                final_snapshot = client.get(
                    f"/api/v1/ai-assistant/runs/{started['runId']}/snapshot"
                ).json()["data"]
                events = client.get(
                    f"/api/v1/ai-assistant/runs/{started['runId']}/events"
                ).json()["data"]["list"]

        self.assertEqual(cancelled.status_code, 200, cancelled.text)
        self.assertFalse(worker.is_alive(), "worker did not stop after no-tool cancellation")
        self.assertEqual(worker_errors, [])
        self.assertEqual(final_snapshot["run"]["status"], "CANCELLED")
        event_types = [event["type"] for event in events]
        self.assertIn("run.cancelled", event_types)
        self.assertNotIn("run.completed", event_types)

    def test_approved_blocking_tool_cancelled_run_does_not_emit_completion(self) -> None:
        tool_started = threading.Event()
        release_tool = threading.Event()
        registry = _blocking_business_write_tool_registry(tool_started=tool_started, release_tool=release_tool)
        self._tool_registry = registry
        worker_errors: list[BaseException] = []
        approval_errors: list[BaseException] = []

        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Cancel approval resume"}).json()[
                "data"
            ]["id"]
            started = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json={
                    "message": "审批通过后阻塞工具并取消",
                    "idempotencyKey": "streaming-e2e-cancel-approved-blocking-tool",
                    "modelMode": "deterministic",
                    "approvalMode": "smart_approval",
                    "toolName": "blocking_business_write",
                    "toolInput": {"message": "approval resume should not complete after cancel"},
                },
            ).json()["data"]
            self._process_run_with_registry(started["runId"], worker_errors, registry)
            approval_id = client.get("/api/v1/ai-assistant/approvals").json()["data"]["list"][0]["id"]
            approval_worker = threading.Thread(
                target=lambda: self._approve_with_registry(approval_id, approval_errors, registry),
                daemon=True,
            )
            approval_worker.start()
            self.assertTrue(tool_started.wait(timeout=5), "approved tool did not start")
            cancelled = client.post(f"/api/v1/ai-assistant/runs/{started['runId']}/cancel", json={"actorId": "uat"})
            cancelled_snapshot = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/snapshot").json()["data"]
            release_tool.set()
            approval_worker.join(timeout=5)
            final_snapshot = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/snapshot").json()["data"]
            events = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/events").json()["data"]["list"]

        self.assertEqual(worker_errors, [])
        self.assertEqual(cancelled.status_code, 200, cancelled.text)
        self.assertEqual(cancelled_snapshot["run"]["status"], "CANCELLED")
        self.assertFalse(approval_worker.is_alive(), "approval resume did not finish after tool release")
        self.assertEqual(approval_errors, [])
        self.assertEqual(final_snapshot["run"]["status"], "CANCELLED")
        event_types = [event["type"] for event in events]
        self.assertIn("approval.granted", event_types)
        self.assertIn("run.cancelled", event_types)
        self.assertNotIn("run.completed", event_types)
        if "task.completed" in event_types:
            self.fail(f"task.completed leaked after cancellation: {event_types}")

    def test_deterministic_worker_records_text_delta_before_terminal_completion_for_browser_uat(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Deterministic stream"}).json()[
                "data"
            ]["id"]
            started = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json={
                    "message": "deterministic worker should stream before terminal",
                    "idempotencyKey": "streaming-e2e-deterministic-worker-delta",
                    "modelMode": "deterministic",
                    "approvalMode": "smart_approval",
                },
            ).json()["data"]

            self._process_run(started["runId"])
            events = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/events").json()["data"]["list"]

        first_delta = next(event for event in events if event["type"] == "text.delta")
        completed = next(event for event in events if event["type"] == "run.completed")
        self.assertLess(first_delta["sequence"], completed["sequence"])
        self.assertEqual(first_delta["payload"]["model"], "deterministic")
        self.assertEqual(first_delta["payload"]["source"], "harness_final_answer")

    def test_deterministic_worker_reconnect_replays_synthetic_delta_before_completion(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Reconnect synthetic"}).json()[
                "data"
            ]["id"]
            started = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json={
                    "message": "deterministic reconnect should classify synthetic delta",
                    "idempotencyKey": "streaming-e2e-reconnect-synthetic-delta",
                    "modelMode": "deterministic",
                    "approvalMode": "smart_approval",
                },
            ).json()["data"]
            self._process_run(started["runId"])
            events = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/events").json()["data"]["list"]
            first_delta = next(event for event in events if event["type"] == "text.delta")
            with client.stream(
                "GET",
                f"/api/v1/ai-assistant/runs/{started['runId']}/events/stream?_testLimit=6",
                headers={"Last-Event-ID": str(first_delta["sequence"] - 1)},
            ) as resumed_response:
                resumed = _read_sse_frames(resumed_response, 6)

        replayed_events = [frame["data"] for frame in resumed if frame["event"] == "ai_assistant_event"]
        replayed_delta = next(event for event in replayed_events if event["type"] == "text.delta")
        replayed_completed = next(event for event in replayed_events if event["type"] == "run.completed")
        self.assertLess(replayed_delta["sequence"], replayed_completed["sequence"])
        self.assertFalse(replayed_delta["payload"]["streaming"])
        self.assertFalse(replayed_delta["payload"]["raw"])
        self.assertTrue(replayed_delta["payload"]["synthetic"])

    def test_synthetic_model_stream_chunk_metadata_matches_text_delta(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Synthetic chunk"}).json()[
                "data"
            ]["id"]
            started = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                json={
                    "message": "synthetic model stream chunk should be explicit",
                    "idempotencyKey": "streaming-e2e-synthetic-stream-chunk",
                    "modelMode": "deterministic",
                    "approvalMode": "smart_approval",
                },
            ).json()["data"]
            self._process_run(started["runId"])
            events = client.get(f"/api/v1/ai-assistant/runs/{started['runId']}/events").json()["data"]["list"]

        delta = next(event for event in events if event["type"] == "text.delta")
        chunk = next(event for event in events if event["type"] == "model.stream_chunk")
        self.assertEqual(chunk["sequence"], delta["sequence"] + 1)
        self.assertFalse(chunk["payload"]["streaming"])
        self.assertFalse(chunk["payload"]["raw"])
        self.assertTrue(chunk["payload"]["synthetic"])

    def _service_override(self) -> Generator[AiAssistantHarnessService, None, None]:
        with self._factory() as session:
            yield AiAssistantHarnessService(
                AiAssistantRepository(session),
                tool_registry=self._tool_registry,
                live_planner=QwenLivePlanner(
                    LivePlannerConfig(
                        base_url="https://openrouter.ai/api/v1",
                        model="qwen/qwen3.6-27b",
                        api_key_ref="env:OPENROUTER_API_KEY",
                        provider="openrouter",
                    ),
                    client=self._fake_client,
                ),
            )

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session

    def _process_run(self, run_id: int) -> None:
        with self._factory() as session:
            result = AiAssistantHarnessService(
                AiAssistantRepository(session),
                live_planner=QwenLivePlanner(
                    LivePlannerConfig(
                        base_url="https://openrouter.ai/api/v1",
                        model="qwen/qwen3.6-27b",
                        api_key_ref="env:OPENROUTER_API_KEY",
                        provider="openrouter",
                    ),
                    client=self._fake_client,
                ),
            ).process_queued_run(run_id)
            self.assertIsNotNone(result)

    def _process_run_capturing_errors(self, run_id: int, errors: list[BaseException]) -> None:
        try:
            self._process_run(run_id)
        except BaseException as exc:  # pragma: no cover - failure surfaced by test assertion
            errors.append(exc)

    def _process_run_with_registry(
        self,
        run_id: int,
        errors: list[BaseException],
        registry: ToolRegistry,
    ) -> None:
        try:
            with self._factory() as session:
                result = AiAssistantHarnessService(
                    AiAssistantRepository(session),
                    tool_registry=registry,
                ).process_queued_run(run_id)
                self.assertIsNotNone(result)
        except BaseException as exc:  # pragma: no cover - failure surfaced by test assertion
            errors.append(exc)

    def _approve_with_registry(
        self,
        approval_id: int,
        errors: list[BaseException],
        registry: ToolRegistry,
    ) -> None:
        try:
            with self._factory() as session:
                AiAssistantHarnessService(
                    AiAssistantRepository(session),
                    tool_registry=registry,
                ).approve(approval_id, "uat")
        except BaseException as exc:  # pragma: no cover - failure surfaced by test assertion
            errors.append(exc)


class FakeDeltaChatClient(FakeOpenAIChatClient):
    def __init__(self, *, streamed_chunks: list[str], response_payload: dict[str, Any]) -> None:
        super().__init__(response_payload=response_payload)
        self._streamed_chunks = streamed_chunks

    def stream_complete(self, payload: dict[str, Any], on_delta=None) -> dict[str, Any]:
        self.captured_payload = payload
        self.captured_payloads.append(payload)
        if on_delta is not None:
            for chunk in self._streamed_chunks:
                on_delta(chunk)
        if self._response_payload is None:
            raise AssertionError("response payload is required for stream_complete")
        return self._response_payload


class BlockingDeltaChatClient(FakeDeltaChatClient):
    def __init__(self, *, streamed_chunks: list[str], response_payload: dict[str, Any]) -> None:
        super().__init__(streamed_chunks=streamed_chunks, response_payload=response_payload)
        self.first_delta_sent = threading.Event()
        self.release_completion = threading.Event()

    def stream_complete(self, payload: dict[str, Any], on_delta=None) -> dict[str, Any]:
        self.captured_payload = payload
        self.captured_payloads.append(payload)
        if on_delta is not None:
            first, *rest = self._streamed_chunks
            on_delta(first)
            self.first_delta_sent.set()
            if not self.release_completion.wait(timeout=5):
                raise AssertionError("timed out waiting for test to release completion")
            for chunk in rest:
                on_delta(chunk)
        if self._response_payload is None:
            raise AssertionError("response payload is required for stream_complete")
        return self._response_payload


def _blocking_tool_registry(*, tool_started: threading.Event, release_tool: threading.Event) -> ToolRegistry:
    manifest = ToolManifest(
        name="blocking_echo",
        description="Blocks until the test releases the deterministic tool.",
        input_schema={"type": "object", "properties": {"message": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"echo": {"type": "string"}}},
        timeout_ms=5000,
        risk_level=RiskLevel.READ,
        read_resources=["session:{session_id}"],
        write_resources=[],
        policy_ref="ai_assistant_read_only",
    )

    def handler(payload: dict[str, Any]) -> ToolResult:
        tool_started.set()
        if not release_tool.wait(timeout=5):
            raise AssertionError("timed out waiting for deterministic tool release")
        return ToolResult(status="COMPLETED", output={"echo": str(payload.get("message") or "")})

    return ToolRegistry({"blocking_echo": (manifest, handler)})


def _blocking_business_write_tool_registry(
    *,
    tool_started: threading.Event,
    release_tool: threading.Event,
) -> ToolRegistry:
    manifest = ToolManifest(
        name="blocking_business_write",
        description="Blocks after approval until the test releases the business-write tool.",
        input_schema={"type": "object", "properties": {"message": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"echo": {"type": "string"}}},
        timeout_ms=5000,
        risk_level=RiskLevel.BUSINESS_WRITE,
        read_resources=[],
        write_resources=["business:approval-resume"],
        policy_ref="ai_assistant_business_write_requires_approval",
    )

    def handler(payload: dict[str, Any]) -> ToolResult:
        tool_started.set()
        if not release_tool.wait(timeout=5):
            raise AssertionError("timed out waiting for approved tool release")
        return ToolResult(status="COMPLETED", output={"echo": str(payload.get("message") or "")})

    return ToolRegistry({"blocking_business_write": (manifest, handler)})


def _read_sse_frames(response, count: int) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    current_event = "message"
    for line in response.iter_lines():
        if not line:
            continue
        if line.startswith("event: "):
            current_event = line.removeprefix("event: ").strip()
            continue
        if line.startswith("data: "):
            frames.append({"event": current_event, "data": json.loads(line.removeprefix("data: "))})
            current_event = "message"
            if len(frames) >= count:
                return frames
    raise AssertionError(f"Expected {count} SSE frames, got {len(frames)}")


def _read_sse_until_event_type(response, expected_type: str) -> dict[str, Any]:
    current_event = "message"
    for line in response.iter_lines():
        if not line:
            continue
        if line.startswith("event: "):
            current_event = line.removeprefix("event: ").strip()
            continue
        if line.startswith("data: "):
            frame = {"event": current_event, "data": json.loads(line.removeprefix("data: "))}
            current_event = "message"
            if frame["event"] == "ai_assistant_event" and frame["data"]["type"] == expected_type:
                return frame
    raise AssertionError(f"Expected SSE event type {expected_type}")


if __name__ == "__main__":
    unittest.main()
