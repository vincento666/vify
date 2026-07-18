import json
import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient

from app.main import app
from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
from app.modules.ai_assistant.infra.event_stream_reader import (
    AiAssistantEventStreamPage,
)
from app.modules.ai_assistant.web.router import (
    get_ai_assistant_event_stream_reader,
    get_ai_assistant_service,
)
from tests.support.ai_assistant_memory_repo import InMemoryAiAssistantRepository


class AiAssistantLiveStreamApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self._repository = InMemoryAiAssistantRepository()
        app.dependency_overrides[get_ai_assistant_service] = self._service_override
        app.dependency_overrides[get_ai_assistant_event_stream_reader] = (
            lambda: _InMemoryEventStreamReader(self._repository)
        )

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_ai_assistant_service, None)
        app.dependency_overrides.pop(get_ai_assistant_event_stream_reader, None)

    def test_events_stream_replays_persisted_events_and_resumes_after_sequence(self) -> None:
        client = TestClient(app)
        try:
            created = client.post("/api/v1/ai-assistant/sessions", json={"title": "AI Assistant SSE"})
            session_id = created.json()["data"]["id"]
            turn = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={"message": "Echo this contract", "idempotencyKey": "ai-assistant-stream-1"},
            )
            run_id = turn.json()["data"]["runId"]
            listed = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events")
            with client.stream(
                "GET",
                f"/api/v1/ai-assistant/runs/{run_id}/events/stream?afterSequence=0&_testLimit=2",
            ) as response:
                first_events = _read_sse_events(response, 2)
            with client.stream(
                "GET",
                f"/api/v1/ai-assistant/runs/{run_id}/events/stream?afterSequence=1&_testLimit=1",
            ) as resumed_response:
                resumed_events = _read_sse_events(resumed_response, 1)
        finally:
            client.close()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/event-stream"))
        self.assertEqual(first_events[0]["sequence"], 1)
        self.assertEqual(first_events[0]["type"], listed.json()["data"]["list"][0]["type"])
        self.assertEqual(first_events[1]["sequence"], 2)
        self.assertEqual(resumed_events[0]["sequence"], 2)

    def _service_override(self) -> Generator[AiAssistantHarnessService, None, None]:
        yield AiAssistantHarnessService(self._repository)


class _InMemoryEventStreamReader:
    def __init__(self, repository: InMemoryAiAssistantRepository) -> None:
        self._repository = repository

    def read(
        self,
        run_id: int,
        *,
        after_sequence: int,
    ) -> AiAssistantEventStreamPage:
        run = self._repository.get_run(run_id)
        if run is None:
            raise KeyError(run_id)
        return AiAssistantEventStreamPage(
            run=run,
            events=self._repository.list_run_events(
                run_id,
                after_sequence=after_sequence,
            ),
        )


def _read_sse_events(response, count: int) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for line in response.iter_lines():
        if not line or not line.startswith("data: "):
            continue
        events.append(json.loads(line.removeprefix("data: ")))
        if len(events) >= count:
            break
    return events


if __name__ == "__main__":
    unittest.main()
