from pathlib import Path

from app.modules.realtime_transport.domain.decision import evaluate_realtime_transport


def test_sse_durable_polling_remains_default_without_insufficiency_evidence() -> None:
    decision = evaluate_realtime_transport(
        {
            "sseReconnectProven": True,
            "durablePollingProven": True,
            "bidirectionalControlRequired": False,
            "multiInstanceFanoutRequired": False,
            "measuredSseLimitation": "",
        }
    )

    assert decision["decision"] == "no_go"
    assert decision["defaultTransport"] == "sse_plus_durable_polling"
    assert decision["durableEventStoreSourceOfTruth"] is True
    assert decision["deliverySemantics"] == "at_least_once_idempotent_client"
    assert decision["websocket"]["status"] == "not_justified"
    assert decision["redisPubsub"]["status"] == "not_justified"
    assert decision["reconnect"]["cursor"] == "afterSequence"
    assert decision["heartbeat"]["transport"] == "sse_comment"
    assert decision["backpressure"]["mvpBound"] == "single_process_testclient_and_browser_uat"


def test_websocket_requires_bidirectional_control_or_measured_sse_limit() -> None:
    decision = evaluate_realtime_transport(
        {
            "sseReconnectProven": True,
            "durablePollingProven": True,
            "bidirectionalControlRequired": True,
            "multiInstanceFanoutRequired": False,
            "measuredSseLimitation": "operator interrupt must reach an in-flight worker within one run",
        }
    )

    assert decision["decision"] == "needs_spike"
    assert decision["websocket"]["status"] == "candidate"
    assert decision["redisPubsub"]["status"] == "not_justified"


def test_adr_records_no_go_and_transport_bounds() -> None:
    adr = Path("docs/adr/0004-realtime-control-scaleout-transport.md").read_text()

    assert "Decision: NO-GO for WebSocket and Redis/pubsub" in adr
    assert "SSE + durable polling remains the default" in adr
    assert "Last-Event-ID" in adr
    assert "afterSequence" in adr
    assert "at-least-once" in adr
    assert "single-process MVP" in adr
