from datetime import datetime, timedelta

from app.modules.workflow.domain.service import (
    _chatflow_explicit_session_id,
    _chatflow_session_status,
    _is_expired,
    _needs_persisted_history,
    _message_events_from_node_runs,
    _result_variable_scopes,
    _stream_events_from_node_runs,
)


def test_chatflow_session_status_maps_runtime_status() -> None:
    assert _chatflow_session_status("INTERRUPTED") == "waiting"
    assert _chatflow_session_status("SUCCEEDED") == "completed"
    assert _chatflow_session_status("FAILED") == "failed"
    assert _chatflow_session_status("RUNNING") == "active"


def test_message_events_from_node_runs_keeps_done_message_without_delta_duplication() -> None:
    events = _message_events_from_node_runs(
        [
            {
                "node_key": "message_1",
                "outputs": {
                    "events": [
                        {"type": "message_delta", "nodeKey": "message_1", "content": "hello"},
                        {"type": "message_done", "nodeKey": "message_1", "content": "hello"},
                    ]
                },
            }
        ]
    )

    assert events == [{"nodeKey": "message_1", "content": "hello", "rawType": "message_done"}]


def test_stream_events_from_node_runs_keeps_deltas_and_synthesizes_end_output() -> None:
    events = _stream_events_from_node_runs(
        [
            {
                "node_key": "message_1",
                "node_type": "MESSAGE",
                "outputs": {
                    "events": [
                        {"type": "message_delta", "nodeKey": "message_1", "content": "hello"},
                        {"type": "message_done", "nodeKey": "message_1", "content": "hello"},
                    ]
                },
            },
            {
                "node_key": "end",
                "node_type": "END",
                "outputs": {"final": "done"},
            },
        ]
    )

    assert events == [
        {"type": "message_delta", "nodeKey": "message_1", "content": "hello"},
        {"type": "message_done", "nodeKey": "message_1", "content": "hello"},
        {"type": "message_delta", "nodeKey": "end", "content": "done"},
        {"type": "message_done", "nodeKey": "end", "content": "done"},
    ]


def test_stream_events_from_node_runs_keeps_node_usage_projection() -> None:
    events = _stream_events_from_node_runs(
        [
            {
                "node_key": "llm_1",
                "node_type": "LLM",
                "outputs": {
                    "events": [
                        {
                            "type": "node_usage",
                            "nodeKey": "llm_1",
                            "inputTokens": 12,
                            "outputTokens": 8,
                            "totalTokens": 20,
                            "costEstimate": "0.001",
                        }
                    ]
                },
            }
        ]
    )

    assert events == [
        {
            "type": "node_usage",
            "nodeKey": "llm_1",
            "content": "",
            "inputTokens": 12,
            "outputTokens": 8,
            "totalTokens": 20,
            "costEstimate": "0.001",
        }
    ]


def test_history_injection_requires_explicit_session_and_include_history_node() -> None:
    assert _chatflow_explicit_session_id({"sys.conversation_id": "conv-1"}) == "conv-1"
    assert _chatflow_explicit_session_id({"sys.query": "no session"}) == ""
    assert _needs_persisted_history(
        [
            {"type": "MESSAGE", "config": {"includeHistory": True}},
            {"type": "INFORMATION_COLLECTION", "config": {"includeHistory": True}},
        ]
    )
    assert not _needs_persisted_history([{"type": "INFORMATION_COLLECTION", "config": {"includeHistory": False}}])


def test_result_variable_scopes_normalizes_mapping_values() -> None:
    class Result:
        variable_scopes = {"conversation": {"topic": "refund"}, "bad": "ignored"}

    assert _result_variable_scopes(Result()) == {"conversation": {"topic": "refund"}}


def test_is_expired_only_matches_past_datetimes() -> None:
    assert _is_expired(datetime.now() - timedelta(seconds=1))
    assert not _is_expired(datetime.now() + timedelta(seconds=1))
    assert not _is_expired(None)
