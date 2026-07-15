import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.database import get_session
from app.core.responses import success
from app.main import app
from app.modules.runtime_lab.web import router as runtime_lab_router
from app.modules.runtime_lab.web.router import get_runtime_lab_service


class _ClosableSession:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_runtime_lab_sop_stream_relays_child_lifecycle_before_terminal_event() -> None:
    payload = {
        "sessionId": 17,
        "runId": 42,
        "status": "RUNNING",
        "reply": "Chatflow SOP 正在后台执行，请稍候。",
        "activeTask": {
            "id": 9,
            "chatflowSession": {
                "runId": 42,
                "eventStreamRef": "/api/v1/runtime-runs/42/events/stream?afterSequence=0",
            },
        },
    }
    child_events = [
        {
            "sequence": 1,
            "type": "workflow_run_started",
            "nodeKey": None,
            "payload": {"runId": 42},
        },
        {
            "sequence": 2,
            "type": "workflow_run_interrupted",
            "nodeKey": "collect_phone",
            "payload": {"output": {"prompt": "请输入手机号"}},
        },
    ]
    read_calls: list[tuple[int, int, int]] = []

    def read_child_events(run_id: int, after_sequence: int, count: int) -> list[dict[str, object]]:
        read_calls.append((run_id, after_sequence, count))
        if after_sequence == 0:
            return [child_events[0]]
        if after_sequence == 1:
            return [child_events[1]]
        return []

    request_session = _ClosableSession()
    app.dependency_overrides[get_runtime_lab_service] = lambda: object()
    app.dependency_overrides[get_session] = lambda: request_session
    try:
        with (
            patch.object(
                runtime_lab_router,
                "_runtime_lab_active_child_cursor",
                return_value=None,
            ),
            patch.object(
                runtime_lab_router,
                "_post_runtime_lab_message_with_metadata",
                return_value=(success(payload), False),
            ),
            patch.object(
                runtime_lab_router,
                "_runtime_lab_child_event_reader",
                return_value=read_child_events,
                create=True,
            ),
            patch.object(
                runtime_lab_router,
                "_runtime_lab_child_result_reader",
                return_value=lambda _run_id: {
                    "status": "INTERRUPTED",
                    "output": {"interrupt": {"question": "请输入手机号"}},
                },
                create=True,
            ),
            patch.object(
                runtime_lab_router,
                "_runtime_lab_resume_job_reader",
                return_value=lambda _job_id: None,
                create=True,
            ),
            TestClient(app) as client,
        ):
            response = client.post(
                "/api/v1/runtime-lab/sessions/17/messages:stream?afterSequence=0&heartbeatMs=100",
                json={"message": "我要退票"},
            )
    finally:
        app.dependency_overrides.pop(get_runtime_lab_service, None)
        app.dependency_overrides.pop(get_session, None)

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")
    frames = [
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    assert [frame["type"] for frame in frames] == ["delta", "delta", "done"]
    assert frames[0] == {
        "type": "delta",
        "source": "runtime_lab",
        "sessionId": 17,
        "runId": 42,
        "payload": payload,
    }
    assert frames[1]["source"] == "runtime_v2"
    assert frames[1]["sequence"] == 1
    assert frames[1]["event"]["type"] == "workflow_run_started"
    assert frames[2]["source"] == "runtime_v2"
    assert frames[2]["sequence"] == 2
    assert frames[2]["event"]["type"] == "workflow_run_interrupted"
    assert frames[2]["result"]["reply"] == "请输入手机号"
    assert frames[2]["result"]["runtimeResult"]["status"] == "INTERRUPTED"
    assert read_calls == [(42, 0, 100), (42, 1, 100)]
    assert request_session.closed


def test_new_resume_stream_starts_after_the_pre_command_child_cursor() -> None:
    payload = {
        "sessionId": 17,
        "runId": 42,
        "status": "RUNNING",
        "reply": "Chatflow SOP 正在后台执行，请稍候。",
    }
    child_events = [
        {
            "sequence": 6,
            "type": "workflow_run_resumed",
            "nodeKey": "collect_phone",
            "payload": {"resumeData": {"phone": "13800138000"}},
        },
        {
            "sequence": 7,
            "type": "workflow_run_interrupted",
            "nodeKey": "confirm_1",
            "payload": {"output": {"prompt": "请确认是否继续办理。"}},
        },
    ]
    read_calls: list[int] = []

    def read_child_events(_run_id: int, after_sequence: int, _count: int) -> list[dict[str, object]]:
        read_calls.append(after_sequence)
        return [event for event in child_events if int(event["sequence"]) > after_sequence]

    request_session = _ClosableSession()
    app.dependency_overrides[get_runtime_lab_service] = lambda: object()
    app.dependency_overrides[get_session] = lambda: request_session
    try:
        with (
            patch.object(
                runtime_lab_router,
                "_runtime_lab_active_child_cursor",
                return_value=(42, 5),
                create=True,
            ),
            patch.object(
                runtime_lab_router,
                "_post_runtime_lab_message_with_metadata",
                return_value=(success(payload), False),
                create=True,
            ),
            patch.object(
                runtime_lab_router,
                "_runtime_lab_child_event_reader",
                return_value=read_child_events,
                create=True,
            ),
            patch.object(
                runtime_lab_router,
                "_runtime_lab_child_result_reader",
                return_value=lambda _run_id: {
                    "status": "INTERRUPTED",
                    "output": {"interrupt": {"question": "请确认是否继续办理。"}},
                },
                create=True,
            ),
            patch.object(
                runtime_lab_router,
                "_runtime_lab_resume_job_reader",
                return_value=lambda _job_id: None,
                create=True,
            ),
            TestClient(app) as client,
        ):
            response = client.post(
                "/api/v1/runtime-lab/sessions/17/messages:stream?afterSequence=0&heartbeatMs=100",
                json={"message": "订单号：TK-100，手机号 13800138000"},
            )
    finally:
        app.dependency_overrides.pop(get_runtime_lab_service, None)
        app.dependency_overrides.pop(get_session, None)

    frames = [
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    assert [frame["type"] for frame in frames] == ["delta", "delta", "done"]
    assert [frame.get("sequence") for frame in frames[1:]] == [6, 7]
    assert read_calls == [5]


def test_requeued_resume_failure_event_does_not_terminate_the_new_stream() -> None:
    payload = {"sessionId": 17, "runId": 42, "status": "RUNNING"}
    rows = [
        {
            "sequence": 6,
            "type": "workflow_run_resume_failed",
            "payload": {"error": "provider unavailable", "jobId": 81, "attemptCount": 3},
        },
        {
            "sequence": 7,
            "type": "workflow_run_resumed",
            "payload": {"resumeData": {"phone": "13800138000"}},
        },
        {
            "sequence": 8,
            "type": "workflow_run_interrupted",
            "payload": {"output": {"prompt": "请确认是否继续办理。"}},
        },
    ]

    frames = list(
        runtime_lab_router._iter_runtime_lab_sop_sse(
            session_id=17,
            payload=payload,
            run_id=42,
            after_sequence=5,
            heartbeat_ms=100,
            test_limit=None,
            test_heartbeat_limit=1,
            read_child_events=lambda _run_id, after_sequence, _count: [
                row for row in rows if int(row["sequence"]) > after_sequence
            ],
            read_child_result=lambda _run_id: {
                "status": "INTERRUPTED",
                "output": {"interrupt": {"question": "请确认是否继续办理。"}},
            },
            read_resume_job=lambda _job_id: {"status": "QUEUED", "attempt_count": 0},
        )
    )

    parsed = [json.loads(frame.removeprefix("data: ")) for frame in frames if frame.startswith("data: ")]
    assert [frame["type"] for frame in parsed] == ["delta", "delta", "done"]
    assert [frame.get("sequence") for frame in parsed[1:]] == [7, 8]


def test_runtime_lab_json_message_route_remains_a_json_envelope() -> None:
    payload = {"sessionId": 17, "reply": "legacy JSON remains supported"}

    app.dependency_overrides[get_runtime_lab_service] = lambda: object()
    app.dependency_overrides[get_session] = lambda: object()
    try:
        with (
            patch.object(
                runtime_lab_router,
                "_post_runtime_lab_message",
                return_value=success(payload),
            ),
            TestClient(app) as client,
        ):
            response = client.post(
                "/api/v1/runtime-lab/sessions/17/messages",
                json={"message": "我要退票"},
            )
    finally:
        app.dependency_overrides.pop(get_runtime_lab_service, None)
        app.dependency_overrides.pop(get_session, None)

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["data"] == payload


def test_runtime_lab_sop_stream_projects_provider_chunk_as_incremental_delta() -> None:
    event = {
        "sequence": 7,
        "type": "llm_delta",
        "nodeKey": "policy_llm",
        "payload": {"content": "正在核验", "streamSource": "provider"},
    }

    frame = runtime_lab_router._runtime_lab_child_stream_frame(
        session_id=17,
        run_id=42,
        sequence=7,
        event=event,
        result={},
    )

    assert frame["type"] == "delta"
    assert frame["source"] == "provider"
    assert frame["delta"] == "正在核验"
    assert frame["sequence"] == 7
    assert frame["event"]["type"] == "llm_delta"


def test_runtime_lab_sop_stream_adds_structured_failure_without_breaking_error_string() -> None:
    failure = {
        "code": "WORKFLOW_NODE_TIMEOUT",
        "kind": "timeout",
        "message": "A workflow node timed out.",
        "runId": 42,
        "nodeKey": "policy_llm",
        "nodeType": "LLM",
        "retryable": False,
    }
    event = {
        "sequence": 8,
        "type": "workflow_run_failed",
        "payload": {"error": "Runtime v2 node timed out: policy_llm after 80ms", "failure": failure},
    }

    frame = runtime_lab_router._runtime_lab_child_stream_frame(
        session_id=17,
        run_id=42,
        sequence=8,
        event=event,
        result={},
    )

    assert frame["type"] == "error"
    assert frame["error"] == "Runtime v2 node timed out: policy_llm after 80ms"
    assert frame["failure"] == failure
