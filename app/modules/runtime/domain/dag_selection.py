from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from typing import Any

from app.modules.runtime.api.schemas import NodeSelectionState


def build_runtime_dag_selection_graph(
    *,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    selected_ports: Mapping[str, list[str] | set[str] | tuple[str, ...]] | None = None,
    waiting_node_keys: set[str] | None = None,
    completed_node_keys: set[str] | None = None,
    running_node_keys: set[str] | None = None,
    failed_node_keys: set[str] | None = None,
    cancelled_node_keys: set[str] | None = None,
) -> list[dict[str, Any]]:
    node_order = [_node_key(node) for node in nodes if _node_key(node)]
    order_index = {node_key: index for index, node_key in enumerate(node_order)}
    outgoing: dict[str, list[dict[str, Any]]] = {}
    for edge in edges:
        source = _node_ref(edge, "source")
        if source:
            outgoing.setdefault(source, []).append(edge)

    branch_selection = {
        str(node_key): {str(port_key) for port_key in port_keys}
        for node_key, port_keys in (selected_ports or {}).items()
    }
    selected_upstreams: dict[str, set[str]] = {}
    skipped_upstreams: dict[str, set[str]] = {}
    selected_nodes = {
        _node_key(node)
        for node in nodes
        if _node_key(node) and (str(node.get("type") or "").upper() == "START" or _node_key(node) == "start")
    }
    selected_queue: deque[str] = deque(sorted(selected_nodes, key=lambda key: order_index.get(key, 0)))
    skipped_roots: set[str] = set()

    while selected_queue:
        source = selected_queue.popleft()
        selected_port_keys = branch_selection.get(source)
        for edge in outgoing.get(source, []):
            target = _node_ref(edge, "target")
            if not target:
                continue
            port_key = _edge_source_port_key(edge)
            if selected_port_keys is not None and port_key not in selected_port_keys:
                skipped_upstreams.setdefault(target, set()).add(source)
                skipped_roots.add(target)
                continue
            selected_upstreams.setdefault(target, set()).add(source)
            if target not in selected_nodes:
                selected_nodes.add(target)
                selected_queue.append(target)

    skipped_nodes: set[str] = set()
    skipped_queue: deque[str] = deque(sorted(skipped_roots, key=lambda key: order_index.get(key, 0)))
    while skipped_queue:
        source = skipped_queue.popleft()
        if source in selected_nodes or source in skipped_nodes:
            continue
        skipped_nodes.add(source)
        for edge in outgoing.get(source, []):
            target = _node_ref(edge, "target")
            if not target:
                continue
            skipped_upstreams.setdefault(target, set()).add(source)
            skipped_queue.append(target)

    waiting = waiting_node_keys or set()
    completed = completed_node_keys or set()
    running = running_node_keys or set()
    failed = failed_node_keys or set()
    cancelled = cancelled_node_keys or set()

    states: list[dict[str, Any]] = []
    for node_key in node_order:
        state = _selection_state(
            node_key,
            selected_nodes=selected_nodes,
            skipped_nodes=skipped_nodes,
            skipped_upstreams=skipped_upstreams,
            waiting_node_keys=waiting,
            completed_node_keys=completed,
            running_node_keys=running,
            failed_node_keys=failed,
            cancelled_node_keys=cancelled,
        )
        model = NodeSelectionState(
            nodeKey=node_key,
            state=state,
            selectedUpstreamNodeKeys=_ordered(selected_upstreams.get(node_key, set()), order_index),
            skippedUpstreamNodeKeys=_ordered(skipped_upstreams.get(node_key, set()), order_index),
            reason=_selection_reason(state, node_key, skipped_upstreams),
        )
        states.append(model.model_dump(by_alias=True))
    return states


def _selection_state(
    node_key: str,
    *,
    selected_nodes: set[str],
    skipped_nodes: set[str],
    skipped_upstreams: dict[str, set[str]],
    waiting_node_keys: set[str],
    completed_node_keys: set[str],
    running_node_keys: set[str],
    failed_node_keys: set[str],
    cancelled_node_keys: set[str],
) -> str:
    if node_key in cancelled_node_keys:
        return "cancelled"
    if node_key in failed_node_keys:
        return "failed"
    if node_key in waiting_node_keys:
        return "waiting"
    if node_key in completed_node_keys:
        return "completed"
    if node_key in running_node_keys:
        return "running"
    if node_key in skipped_nodes:
        return "skipped"
    if node_key in selected_nodes:
        return "pending" if skipped_upstreams.get(node_key) else "selected"
    return "pending"


def _selection_reason(state: str, node_key: str, skipped_upstreams: dict[str, set[str]]) -> str:
    if state == "skipped":
        return "branch port not selected"
    if skipped_upstreams.get(node_key):
        return "implicit join waits only for selected upstreams"
    return ""


def _ordered(node_keys: set[str], order_index: dict[str, int]) -> list[str]:
    return sorted(node_keys, key=lambda key: order_index.get(key, len(order_index)))


def _node_key(node: Mapping[str, Any]) -> str:
    return str(node.get("nodeKey") or node.get("node_key") or "").strip()


def _node_ref(edge: Mapping[str, Any], side: str) -> str:
    if side == "source":
        return str(edge.get("sourceNodeKey") or edge.get("source_node_key") or "").strip()
    return str(edge.get("targetNodeKey") or edge.get("target_node_key") or "").strip()


def _edge_source_port_key(edge: Mapping[str, Any]) -> str:
    value = edge.get("sourcePortKey")
    if value is None:
        value = edge.get("source_port_key")
    text = str(value or "").strip()
    if text:
        return text
    condition = edge.get("condition")
    if condition is None:
        condition = edge.get("condition_expr")
    condition_text = str(condition or "").strip()
    return condition_text or "default"
