from app.modules.ai_assistant.domain.streaming_runtime import (
    heartbeat_payload,
    last_sequence,
    stream_fallback_payload,
    text_delta_payload,
)


def test_text_delta_payload_marks_raw_streaming_delta() -> None:
    payload = text_delta_payload(
        index=2,
        delta="好",
        model="qwen/test",
        source="openrouter_delta",
        round_index=1,
    )

    assert payload == {
        "index": 2,
        "delta": "好",
        "chunk": "好",
        "model": "qwen/test",
        "source": "openrouter_delta",
        "streaming": True,
        "raw": True,
        "roundIndex": 1,
    }


def test_stream_fallback_payload_and_cursor_helpers_are_auditable() -> None:
    fallback = stream_fallback_payload(model="qwen/test", source="post_completion_split")
    heartbeat = heartbeat_payload(run_id=7, after_sequence=12)

    assert fallback["reason"] == "provider_non_streaming"
    assert fallback["fallback"] is True
    assert heartbeat["runId"] == 7
    assert heartbeat["afterSequence"] == 12
    assert heartbeat["heartbeatAt"]
    assert last_sequence([{"sequence": 2}, {"sequence": 5}], fallback=1) == 5
    assert last_sequence([], fallback=9) == 9
