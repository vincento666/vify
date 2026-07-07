from app.modules.runtime.domain.scheduler import compute_frontier


def test_frontier_starts_at_start_then_advances_linear_chain() -> None:
    graph = {
        "nodes": [
            {"nodeKey": "start", "type": "START"},
            {"nodeKey": "collect", "type": "HUMAN_INPUT"},
            {"nodeKey": "end", "type": "END"},
        ],
        "edges": [
            {"sourceNodeKey": "start", "targetNodeKey": "collect"},
            {"sourceNodeKey": "collect", "targetNodeKey": "end"},
        ],
    }

    initial = compute_frontier(graph, {})
    after_start = compute_frontier(graph, {"completedNodeKeys": {"start"}})

    assert initial["runnableNodeKeys"] == ["start"]
    assert initial["waitingNodeKeys"] == ["collect", "end"]
    assert after_start["runnableNodeKeys"] == ["collect"]
    assert after_start["waitingNodeKeys"] == ["end"]


def test_frontier_waits_for_all_selected_upstreams_but_ignores_skipped_branch() -> None:
    graph = _branch_join_graph()
    state = {
        "selectedPorts": {"router": ["vip"]},
        "completedNodeKeys": {"start", "router", "vip_a"},
        "runningNodeKeys": {"vip_b"},
    }

    frontier = compute_frontier(graph, state)

    assert frontier["runnableNodeKeys"] == []
    assert frontier["waitingNodeKeys"] == ["join", "end"]
    assert frontier["skippedNodeKeys"] == ["fallback"]


def test_frontier_releases_implicit_join_when_selected_upstreams_complete() -> None:
    graph = _branch_join_graph()
    state = {
        "selectedPorts": {"router": ["vip"]},
        "completedNodeKeys": {"start", "router", "vip_a", "vip_b"},
    }

    frontier = compute_frontier(graph, state)

    assert frontier["runnableNodeKeys"] == ["join"]
    assert frontier["skippedNodeKeys"] == ["fallback"]


def _branch_join_graph() -> dict[str, object]:
    return {
        "nodes": [
            {"nodeKey": "start", "type": "START"},
            {"nodeKey": "router", "type": "CONDITION"},
            {"nodeKey": "vip_a", "type": "MESSAGE"},
            {"nodeKey": "vip_b", "type": "MESSAGE"},
            {"nodeKey": "fallback", "type": "MESSAGE"},
            {"nodeKey": "join", "type": "VARIABLE_AGGREGATION"},
            {"nodeKey": "end", "type": "END"},
        ],
        "edges": [
            {"sourceNodeKey": "start", "targetNodeKey": "router"},
            {"sourceNodeKey": "router", "targetNodeKey": "vip_a", "sourcePortKey": "vip"},
            {"sourceNodeKey": "router", "targetNodeKey": "vip_b", "sourcePortKey": "vip"},
            {"sourceNodeKey": "router", "targetNodeKey": "fallback"},
            {"sourceNodeKey": "vip_a", "targetNodeKey": "join"},
            {"sourceNodeKey": "vip_b", "targetNodeKey": "join"},
            {"sourceNodeKey": "fallback", "targetNodeKey": "join"},
            {"sourceNodeKey": "join", "targetNodeKey": "end"},
        ],
    }
