from __future__ import annotations

from app.modules.runtime.domain.scheduler import compute_frontier


def test_state_graph_propagates_selected_skipped_waiting_and_cancelled_states() -> None:
    graph = _conditional_join_graph()

    frontier = compute_frontier(
        graph,
        {
            "selectedPorts": {"router": ["vip"]},
            "completedNodeKeys": {"start", "router", "vip_message"},
            "waitingNodeKeys": {"join"},
            "cancelledNodeKeys": {"end"},
        },
    )

    states = frontier["stateByNodeKey"]
    assert states["vip_message"]["state"] == "completed"
    assert states["fallback_message"]["state"] == "skipped"
    assert states["join"]["state"] == "waiting"
    assert states["join"]["selectedUpstreamNodeKeys"] == ["vip_message"]
    assert states["join"]["skippedUpstreamNodeKeys"] == ["fallback_message"]
    assert states["join"]["reason"] == "implicit join waits only for selected upstreams"
    assert states["end"]["state"] == "cancelled"


def _conditional_join_graph() -> dict[str, object]:
    return {
        "nodes": [
            {"nodeKey": "start", "type": "START"},
            {"nodeKey": "router", "type": "CONDITION"},
            {"nodeKey": "vip_message", "type": "MESSAGE"},
            {"nodeKey": "fallback_message", "type": "MESSAGE"},
            {"nodeKey": "join", "type": "HUMAN_INPUT"},
            {"nodeKey": "end", "type": "END"},
        ],
        "edges": [
            {"sourceNodeKey": "start", "targetNodeKey": "router"},
            {"sourceNodeKey": "router", "targetNodeKey": "vip_message", "sourcePortKey": "vip"},
            {"sourceNodeKey": "router", "targetNodeKey": "fallback_message"},
            {"sourceNodeKey": "vip_message", "targetNodeKey": "join"},
            {"sourceNodeKey": "fallback_message", "targetNodeKey": "join"},
            {"sourceNodeKey": "join", "targetNodeKey": "end"},
        ],
    }
