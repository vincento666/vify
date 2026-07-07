from __future__ import annotations

import time

from app.core.database import get_session_factory
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository


def test_high_frequency_runtime_events_are_sampled_and_summarized() -> None:
    chatflow_id = int(time.time_ns() % 1_000_000_000)
    run_id = chatflow_id + 10_000
    with get_session_factory()() as session:
        repository = ChatflowStateRepository(session)
        for index in range(12):
            repository.append_event(
                session_id=f"session-{run_id}",
                chatflow_id=chatflow_id,
                run_id=run_id,
                event_type="llm_delta",
                node_key="llm_1",
                payload={"chunk": f"token-{index}"},
            )
        events = repository.list_events(chatflow_id, run_id)

    event_types = [event["event_type"] for event in events]
    summary_events = [event for event in events if event["event_type"] == "runtime_event_summary"]
    assert len(events) < 12
    assert summary_events
    assert event_types.count("llm_delta") <= 5
    assert summary_events[-1]["payload"]["compactedEventType"] == "llm_delta"
    assert summary_events[-1]["payload"]["sampledCount"] >= 6
    assert summary_events[-1]["payload"]["latestPayload"]["chunk"] == "token-11"


def test_critical_runtime_events_are_never_compacted() -> None:
    chatflow_id = int(time.time_ns() % 1_000_000_000)
    run_id = chatflow_id + 20_000
    critical_types = [
        "workflow_run_started",
        "workflow_node_failed",
        "workflow_node_waiting",
        "workflow_run_completed",
        "workflow_run_cancelled",
    ]
    with get_session_factory()() as session:
        repository = ChatflowStateRepository(session)
        for index in range(3):
            for event_type in critical_types:
                repository.append_event(
                    session_id=f"session-{run_id}",
                    chatflow_id=chatflow_id,
                    run_id=run_id,
                    event_type=event_type,
                    node_key="node_1",
                    payload={"index": index, "eventType": event_type},
                )
        events = repository.list_events(chatflow_id, run_id)

    event_types = [event["event_type"] for event in events]
    assert len(events) == len(critical_types) * 3
    assert "runtime_event_summary" not in event_types
    for event_type in critical_types:
        assert event_types.count(event_type) == 3
