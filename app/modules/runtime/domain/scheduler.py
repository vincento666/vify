from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.modules.runtime.domain.dag_selection import build_runtime_dag_selection_graph


def compute_frontier(graph: Mapping[str, Any], state: Mapping[str, Any]) -> dict[str, Any]:
    nodes = _list_of_mappings(graph.get("nodes"))
    edges = _list_of_mappings(graph.get("edges"))
    completed = _key_set(state, "completedNodeKeys", "completed_node_keys")
    running = _key_set(state, "runningNodeKeys", "running_node_keys")
    waiting = _key_set(state, "waitingNodeKeys", "waiting_node_keys")
    failed = _key_set(state, "failedNodeKeys", "failed_node_keys")
    cancelled = _key_set(state, "cancelledNodeKeys", "cancelled_node_keys")
    selected_ports = _selected_ports(state.get("selectedPorts") or state.get("selected_ports"))

    selection = build_runtime_dag_selection_graph(
        nodes=[dict(node) for node in nodes],
        edges=[dict(edge) for edge in edges],
        selected_ports=selected_ports,
        waiting_node_keys=waiting,
        completed_node_keys=completed,
        running_node_keys=running,
        failed_node_keys=failed,
        cancelled_node_keys=cancelled,
    )
    node_types = {_node_key(node): str(node.get("type") or "").upper() for node in nodes}
    runnable: list[str] = []
    blocked: list[str] = []
    skipped: list[str] = []
    state_by_node_key: dict[str, dict[str, Any]] = {}

    for row in selection:
        node_key = str(row["nodeKey"])
        state_name = str(row["state"])
        state_by_node_key[node_key] = dict(row)
        if state_name == "skipped":
            skipped.append(node_key)
            continue
        if state_name in {"completed", "running", "waiting", "failed", "cancelled"}:
            if state_name == "waiting":
                blocked.append(node_key)
            continue
        if not _is_selected_frontier_candidate(node_key, row, node_types):
            continue
        upstreams = [str(upstream) for upstream in row.get("selectedUpstreamNodeKeys") or []]
        if all(upstream in completed for upstream in upstreams):
            runnable.append(node_key)
        else:
            blocked.append(node_key)

    return {
        "runnableNodeKeys": runnable,
        "waitingNodeKeys": blocked,
        "skippedNodeKeys": skipped,
        "stateByNodeKey": state_by_node_key,
    }


def _is_selected_frontier_candidate(node_key: str, row: Mapping[str, Any], node_types: Mapping[str, str]) -> bool:
    if node_key == "start" or node_types.get(node_key) == "START":
        return True
    return bool(row.get("selectedUpstreamNodeKeys") or row.get("skippedUpstreamNodeKeys"))


def _list_of_mappings(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _key_set(state: Mapping[str, Any], *keys: str) -> set[str]:
    for key in keys:
        value = state.get(key)
        if value is not None:
            return {str(item) for item in value if str(item)}
    return set()


def _selected_ports(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, Mapping):
        return {}
    return {
        str(node_key): [str(port_key) for port_key in port_keys if str(port_key)]
        for node_key, port_keys in value.items()
        if isinstance(port_keys, (list, set, tuple))
    }


def _node_key(node: Mapping[str, Any]) -> str:
    return str(node.get("nodeKey") or node.get("node_key") or "").strip()
