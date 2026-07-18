import json
import unittest
from collections.abc import Generator
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
from app.modules.ai_assistant.domain.live_model import LivePlannerConfig, QwenLivePlanner
from app.modules.ai_assistant.infra.event_stream_reader import (
    AiAssistantEventStreamPage,
)
from app.modules.ai_assistant.infra.repository import AiAssistantRepository
from app.modules.ai_assistant.web.router import (
    get_ai_assistant_event_stream_reader,
    get_ai_assistant_service,
)
from app.modules.chat.domain.llm_request import FakeOpenAIChatClient
from tests.support.mysql import mysql8_unittest_database


class AiAssistantStreamingApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_streaming_contract",
            tables=ai_assistant_tables(),
            register=register_ai_assistant_tables,
        )
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        self._fake_client: Any = FakeDeltaChatClient(
            streamed_chunks=["甲", "乙"],
            response_payload=_model_response("甲乙"),
        )
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)
        app.dependency_overrides[get_ai_assistant_service] = self._service_override

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_ai_assistant_service, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_live_provider_deltas_emit_canonical_text_delta_before_completion_and_snapshot_cursor(self) -> None:
        with TestClient(app) as client:
            run_id = self._start_live_run(client, "streaming-contract-delta")
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events").json()["data"]["list"]
            snapshot = client.get(f"/api/v1/ai-assistant/runs/{run_id}/snapshot")

        delta_events = [event for event in events if event["type"] == "text.delta"]
        self.assertEqual([event["payload"]["delta"] for event in delta_events], ["甲", "乙"])
        first_delta_sequence = delta_events[0]["sequence"]
        completed_sequence = next(event["sequence"] for event in events if event["type"] == "model.call_completed")
        self.assertLess(first_delta_sequence, completed_sequence)
        self.assertEqual(snapshot.status_code, 200, snapshot.text)
        self.assertEqual(snapshot.json()["data"]["run"]["id"], run_id)
        self.assertEqual(snapshot.json()["data"]["streamCursor"]["lastSequence"], events[-1]["sequence"])
        self.assertEqual(snapshot.json()["data"]["events"][-1]["sequence"], events[-1]["sequence"])

    def test_sse_resume_honors_last_event_id_and_can_emit_heartbeat(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/ai-assistant/sessions", json={"title": "Streaming cursor"})
            session_id = created.json()["data"]["id"]
            turn = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={"message": "cursor replay", "idempotencyKey": "streaming-contract-cursor"},
            )
            run_id = turn.json()["data"]["runId"]
            event_list = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events").json()["data"]["list"]
            with client.stream(
                "GET",
                f"/api/v1/ai-assistant/runs/{run_id}/events/stream?_testLimit=1",
                headers={"Last-Event-ID": "1"},
            ) as resumed_response:
                resumed = _read_sse_frames(resumed_response, 1)
            last_sequence = event_list[-1]["sequence"]
            with client.stream(
                "GET",
                f"/api/v1/ai-assistant/runs/{run_id}/events/stream?afterSequence={last_sequence}"
                "&heartbeatMs=1&_testHeartbeatLimit=1",
            ) as heartbeat_response:
                heartbeat = _read_sse_frames(heartbeat_response, 1)

        self.assertEqual(resumed[0]["data"]["sequence"], 2)
        self.assertEqual(heartbeat[0]["event"], "heartbeat")
        self.assertEqual(heartbeat[0]["data"]["runId"], run_id)
        self.assertEqual(heartbeat[0]["data"]["afterSequence"], last_sequence)

    def test_non_streaming_live_provider_emits_explicit_fallback_event(self) -> None:
        self._fake_client = FakeOpenAIChatClient(response_payload=_model_response("fallback text"))
        with TestClient(app) as client:
            run_id = self._start_live_run(client, "streaming-contract-fallback")
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events").json()["data"]["list"]

        fallback_events = [event for event in events if event["type"] == "stream.fallback"]
        self.assertEqual(len(fallback_events), 1)
        self.assertEqual(fallback_events[0]["payload"]["reason"], "provider_non_streaming")
        self.assertEqual(fallback_events[0]["payload"]["source"], "post_completion_split")

    def _start_live_run(self, client: TestClient, idempotency_key: str) -> int:
        created = client.post("/api/v1/ai-assistant/sessions", json={"title": "Streaming contract"})
        session_id = created.json()["data"]["id"]
        turn = client.post(
            f"/api/v1/ai-assistant/sessions/{session_id}/messages",
            json={
                "message": "请实时输出",
                "idempotencyKey": idempotency_key,
                "modelMode": "live",
                "approvalMode": "smart_approval",
            },
        )
        self.assertEqual(turn.status_code, 200, turn.text)
        return int(turn.json()["data"]["runId"])

    def _service_override(self) -> Generator[AiAssistantHarnessService, None, None]:
        with self._factory() as session:
            yield AiAssistantHarnessService(
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
            )

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session


class AiAssistantStreamWorkerSeparationContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self._service = _StreamOnlyService()
        app.dependency_overrides[get_ai_assistant_service] = lambda: self._service
        app.dependency_overrides[get_ai_assistant_event_stream_reader] = (
            lambda: _StreamOnlyEventReader(self._service)
        )

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_ai_assistant_service, None)
        app.dependency_overrides.pop(get_ai_assistant_event_stream_reader, None)

    def test_stream_route_subscribes_without_processing_queued_run(self) -> None:
        with TestClient(app) as client:
            with client.stream(
                "GET",
                "/api/v1/ai-assistant/runs/9001/events/stream?heartbeatMs=1&_testHeartbeatLimit=1",
            ) as response:
                heartbeat = _read_sse_frames(response, 1)

        self.assertEqual(heartbeat[0]["event"], "heartbeat")
        self.assertFalse(
            self._service.process_called,
            "SSE stream route must not execute queued runs before returning StreamingResponse",
        )


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


class _StreamOnlyService:
    process_called = False

    def get_run(self, run_id: int) -> dict[str, Any]:
        return {"id": run_id, "session_id": 1, "status": "QUEUED", "input_payload": {}, "response_payload": {}}

    def list_run_events(self, run_id: int, after_sequence: int = 0) -> list[dict[str, Any]]:
        return []

    def process_queued_run(self, run_id: int) -> None:
        self.process_called = True


class _StreamOnlyEventReader:
    def __init__(self, service: _StreamOnlyService) -> None:
        self._service = service

    def read(
        self,
        run_id: int,
        *,
        after_sequence: int,
    ) -> AiAssistantEventStreamPage:
        return AiAssistantEventStreamPage(
            run=self._service.get_run(run_id),
            events=self._service.list_run_events(
                run_id,
                after_sequence=after_sequence,
            ),
        )


def _model_response(content: str) -> dict[str, Any]:
    return {
        "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
    }


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


if __name__ == "__main__":
    unittest.main()
