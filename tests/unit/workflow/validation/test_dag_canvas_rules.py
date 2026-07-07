from app.modules.workflow.domain.graph_validation import validate_branch_edges


def _node(node_key: str, node_type: str, config: dict | None = None) -> dict:
    return {"nodeKey": node_key, "type": node_type, "config": config or {}}


def _edge(source: str, target: str, condition: str | None = None, **extra: object) -> dict:
    return {"sourceNodeKey": source, "targetNodeKey": target, "condition": condition, **extra}


def _codes(nodes: list[dict], edges: list[dict]) -> set[str]:
    return {issue["code"] for issue in validate_branch_edges(nodes, edges)}


def test_canvas_rules_allow_explicit_default_fan_out() -> None:
    nodes = [
        _node("start", "START", {"ports": [{"key": "default", "allowFanOut": True}]}),
        _node("message_1", "MESSAGE"),
        _node("message_2", "MESSAGE"),
        _node("end", "END"),
    ]
    edges = [
        _edge("start", "message_1"),
        _edge("start", "message_2"),
        _edge("message_1", "end"),
        _edge("message_2", "end"),
    ]

    assert _codes(nodes, edges) == set()


def test_canvas_rules_reject_ambiguous_default_fan_out() -> None:
    nodes = [
        _node("start", "START"),
        _node("message_1", "MESSAGE"),
        _node("message_2", "MESSAGE"),
        _node("end", "END"),
    ]
    edges = [
        _edge("start", "message_1"),
        _edge("start", "message_2"),
        _edge("message_1", "end"),
        _edge("message_2", "end"),
    ]

    assert "start.default.fanOut" in _codes(nodes, edges)


def test_canvas_rules_allow_condition_branches_with_default_fallback() -> None:
    nodes = [
        _node("start", "START"),
        _node(
            "router",
            "CONDITION",
            {
                "conditionBranches": [{"key": "vip", "name": "VIP"}],
                "defaultBranch": "normal",
            },
        ),
        _node("vip_reply", "MESSAGE"),
        _node("normal_reply", "MESSAGE"),
        _node("end", "END"),
    ]
    edges = [
        _edge("start", "router"),
        _edge("router", "vip_reply", "vip"),
        _edge("router", "normal_reply"),
        _edge("vip_reply", "end"),
        _edge("normal_reply", "end"),
    ]

    assert _codes(nodes, edges) == set()


def test_canvas_rules_allow_side_effect_terminal_leaf() -> None:
    nodes = [
        _node("start", "START"),
        _node("notify", "API_CALL", {"resourceId": "api-resource:1", "sideEffectTerminal": True}),
        _node("end", "END"),
    ]
    edges = [_edge("start", "notify")]

    assert _codes(nodes, edges) == set()


def test_canvas_rules_allow_implicit_join_from_multiple_selected_upstreams() -> None:
    nodes = [
        _node("start", "START", {"ports": [{"key": "default", "allowFanOut": True}]}),
        _node("fetch_profile", "API_CALL", {"resourceId": "api-resource:1"}),
        _node("fetch_orders", "API_CALL", {"resourceId": "api-resource:2"}),
        _node("join", "VARIABLE_AGGREGATION"),
        _node("end", "END"),
    ]
    edges = [
        _edge("start", "fetch_profile"),
        _edge("start", "fetch_orders"),
        _edge("fetch_profile", "join"),
        _edge("fetch_orders", "join"),
        _edge("join", "end"),
    ]

    assert _codes(nodes, edges) == set()


def test_canvas_rules_reject_connected_island_not_reachable_from_start() -> None:
    nodes = [
        _node("start", "START"),
        _node("message_1", "MESSAGE"),
        _node("island_1", "MESSAGE"),
        _node("end", "END"),
    ]
    edges = [
        _edge("start", "message_1"),
        _edge("message_1", "end"),
        _edge("island_1", "end"),
    ]

    assert "island_1.island" in _codes(nodes, edges)
