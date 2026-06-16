from __future__ import annotations

from typing import Any


def evaluate_realtime_transport(evidence: dict[str, Any]) -> dict[str, Any]:
    bidirectional_control = bool(evidence.get("bidirectionalControlRequired"))
    multi_instance_fanout = bool(evidence.get("multiInstanceFanoutRequired"))
    measured_sse_limitation = str(evidence.get("measuredSseLimitation") or "").strip()
    needs_websocket = bidirectional_control or bool(measured_sse_limitation)
    needs_redis = multi_instance_fanout
    decision = "needs_spike" if needs_websocket or needs_redis else "no_go"
    return {
        "decision": decision,
        "defaultTransport": "sse_plus_durable_polling",
        "durableEventStoreSourceOfTruth": True,
        "deliverySemantics": "at_least_once_idempotent_client",
        "websocket": {
            "status": "candidate" if needs_websocket else "not_justified",
            "requiredEvidence": "bidirectional control or measured SSE limitation",
        },
        "redisPubsub": {
            "status": "candidate" if needs_redis else "not_justified",
            "requiredEvidence": "multi-process or multi-instance fanout requirement",
            "missRecovery": "durable_event_store_replay",
        },
        "reconnect": {
            "cursor": "afterSequence",
            "lastEventIdHeader": "Last-Event-ID",
            "recoverFrom": "durable_event_store",
        },
        "heartbeat": {
            "transport": "sse_comment",
            "minimumMs": 100,
            "maximumMs": 30000,
        },
        "authorization": {
            "scope": "run_session_tenant",
            "currentMvp": "session_or_run_bound_api_dependencies",
        },
        "backpressure": {
            "mvpBound": "single_process_testclient_and_browser_uat",
            "maxConnections": "not_expanded_without_scaleout_evidence",
        },
        "runtimeSemantics": {
            "taskWorkerChatflowWorkflowSemanticsChanged": False,
            "sopRouterCompatibilityRequired": True,
        },
    }
