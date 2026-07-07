from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

_TEMPLATE_REF_PATTERN = re.compile(r"\{\{\s*([A-Za-z0-9_-]+)\.([A-Za-z0-9_.-]+)\s*\}\}")
_SCOPE_NAMES = {"input", "external", "flow", "global", "conversation", "user", "channel", "sys"}
_READ_ONLY_SCOPES = {"sys"}
_ERROR_BRANCH_NODE_TYPES = {"LLM", "API_CALL", "TOOL_CALL", "CODE", "EXECUTE_WORKFLOW", "AGENT_CALL"}
_SUPPORTED_OUTPUT_TYPES = {"string", "number", "integer", "boolean", "object", "array", "any"}
_SUPPORTED_WRITE_MODES = {"set", "append", "clear"}
_SUPPORTED_ERROR_BEHAVIORS = {"fail", "continue", "branch", "partial"}


def validate_node_endpoints(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> list[dict[str, str]]:
    outgoing: dict[str, set[str | None]] = {}
    for edge in edges:
        source = _node_ref(edge, "source")
        if not source:
            continue
        outgoing.setdefault(source, set()).add(_edge_condition(edge))

    issues: list[dict[str, str]] = []
    for node in nodes:
        node_type = str(node.get("type") or "").upper()
        node_key = _node_key(node)
        if not node_key:
            continue
        if node_type == "END":
            continue
        conditions = outgoing.get(node_key, set())
        config = node.get("config") if isinstance(node.get("config"), Mapping) else {}
        if _requires_error_branch(node_type, config):
            if "error" not in conditions:
                issues.append(
                    {
                        "nodeKey": node_key,
                        "nodeType": node_type,
                        "branchKey": "error",
                        "branchType": "error",
                        "code": f"{node_key}.error",
                        "message": f"{node_key} error branch must connect downstream",
                    }
                )
            if None not in conditions and "success" not in conditions:
                issues.append(
                    {
                        "nodeKey": node_key,
                        "nodeType": node_type,
                        "branchKey": "success",
                        "branchType": "success",
                        "code": f"{node_key}.success",
                        "message": f"{node_key} success outlet must connect downstream",
                    }
                )
            continue
        if node_type == "CONDITION":
            for branch_key in _condition_branch_keys(config):
                if branch_key not in conditions:
                    issues.append(
                        {
                            "nodeKey": node_key,
                            "nodeType": node_type,
                            "branchKey": branch_key,
                            "branchType": "branch",
                            "code": f"{node_key}.{branch_key}",
                            "message": f"{node_key} branch {branch_key} must connect downstream",
                        }
                    )
            if None not in conditions:
                issues.append(
                    {
                        "nodeKey": node_key,
                        "nodeType": node_type,
                        "branchKey": "default",
                        "branchType": "default",
                        "code": f"{node_key}.default",
                        "message": f"{node_key} default branch must connect downstream",
                    }
                )
            continue
        if node_type == "INTENT_RECOGNITION":
            for intent_key in _intent_branch_keys(config):
                if intent_key not in conditions:
                    issues.append(
                        {
                            "nodeKey": node_key,
                            "nodeType": node_type,
                            "branchKey": intent_key,
                            "branchType": "intent",
                            "code": f"{node_key}.{intent_key}",
                            "message": f"{node_key} intent {intent_key} must connect downstream",
                        }
                    )
            if None not in conditions:
                issues.append(
                    {
                        "nodeKey": node_key,
                        "nodeType": node_type,
                        "branchKey": "default",
                        "branchType": "fallback",
                        "code": f"{node_key}.default",
                        "message": f"{node_key} fallback branch must connect downstream",
                    }
                )
            continue
        if not conditions and _is_side_effect_terminal(node, edges):
            continue
        if None not in conditions:
            issues.append(
                {
                    "nodeKey": node_key,
                    "nodeType": node_type,
                    "branchKey": "default",
                    "branchType": "default",
                    "code": f"{node_key}.default",
                    "message": f"{node_key} default outlet must connect downstream",
                }
            )
    issues.extend(_validate_fan_out(nodes, edges))
    issues.extend(_validate_reachable_from_start(nodes, edges))
    return issues


def validate_branch_edges(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> list[dict[str, str]]:
    return validate_node_endpoints(nodes, edges)


def validate_variable_references(nodes: list[dict[str, Any]]) -> list[dict[str, str]]:
    node_keys = {_node_key(node) for node in nodes if _node_key(node)}
    issues: list[dict[str, str]] = []
    for node in nodes:
        node_key = _node_key(node)
        if not node_key:
            continue
        config = node.get("config") if isinstance(node.get("config"), Mapping) else {}
        for scope, variable_name in _template_references(config):
            if scope in _SCOPE_NAMES or scope in node_keys:
                continue
            issues.append(
                {
                    "nodeKey": node_key,
                    "nodeType": str(node.get("type") or "").upper(),
                    "code": f"{node_key}.{scope}.{variable_name}",
                    "message": f"{node_key} references unknown variable {scope}.{variable_name}",
                }
            )
    return issues


def validate_node_contracts(nodes: list[dict[str, Any]]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for node in nodes:
        node_key = _node_key(node)
        if not node_key:
            continue
        node_type = str(node.get("type") or "").upper()
        config = node.get("config") if isinstance(node.get("config"), Mapping) else {}
        issues.extend(_validate_common_contract(node_key, node_type, config))
        if node_type == "CODE":
            if not str(config.get("code") or "").strip():
                issues.append(_issue(node_key, node_type, "code", f"{node_key} code is required"))
        elif node_type == "VARIABLE_ASSIGN":
            issues.extend(_validate_variable_assign_contract(node_key, node_type, config))
        elif node_type == "INFORMATION_COLLECTION":
            fields = config.get("fields")
            if not isinstance(fields, list) or not fields:
                issues.append(_issue(node_key, node_type, "fields", f"{node_key} fields are required"))
            elif isinstance(fields, list):
                issues.extend(_validate_parameter_list(node_key, node_type, "fields", fields))
        elif node_type == "LLM":
            issues.extend(_validate_llm_contract(node_key, node_type, config))
        elif node_type == "API_CALL":
            issues.extend(_validate_api_call_contract(node_key, node_type, config))
        elif node_type == "TOOL_CALL":
            issues.extend(_validate_tool_call_contract(node_key, node_type, config))
        elif node_type == "EXECUTE_WORKFLOW":
            raw_target_id = config.get("targetWorkflowId") or config.get("target_workflow_id") or config.get("workflowId")
            if raw_target_id not in (None, "") and not _is_optional_int(raw_target_id):
                issues.append(_issue(node_key, node_type, "targetWorkflowId", f"{node_key} targetWorkflowId must be numeric"))
        elif node_type == "AGENT_CALL":
            raw_agent_id = config.get("targetAgentId") or config.get("target_agent_id") or config.get("agentId")
            if raw_agent_id not in (None, "") and not _is_optional_int(raw_agent_id):
                issues.append(_issue(node_key, node_type, "targetAgentId", f"{node_key} targetAgentId must be numeric"))
    return issues


def _node_key(node: Mapping[str, Any]) -> str:
    return str(node.get("nodeKey") or node.get("node_key") or "").strip()


def _node_ref(edge: Mapping[str, Any], side: str) -> str:
    if side == "source":
        return str(edge.get("sourceNodeKey") or edge.get("source_node_key") or "").strip()
    return str(edge.get("targetNodeKey") or edge.get("target_node_key") or "").strip()


def _edge_condition(edge: Mapping[str, Any]) -> str | None:
    value = edge.get("condition")
    if value is None:
        value = edge.get("condition_expr")
    text = str(value or "").strip()
    return text or None


def _edge_source_port_key(edge: Mapping[str, Any]) -> str:
    value = edge.get("sourcePortKey")
    if value is None:
        value = edge.get("source_port_key")
    text = str(value or "").strip()
    if text:
        return text
    return _edge_condition(edge) or "default"


def _validate_fan_out(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> list[dict[str, str]]:
    nodes_by_key = {_node_key(node): node for node in nodes if _node_key(node)}
    targets_by_source_port: dict[tuple[str, str], set[str]] = {}
    for edge in edges:
        source = _node_ref(edge, "source")
        target = _node_ref(edge, "target")
        if not source or not target:
            continue
        port_key = _edge_source_port_key(edge)
        targets_by_source_port.setdefault((source, port_key), set()).add(target)

    issues: list[dict[str, str]] = []
    for (source, port_key), targets in targets_by_source_port.items():
        if len(targets) <= 1:
            continue
        node = nodes_by_key.get(source)
        if node is None or _allows_fan_out(node, port_key):
            continue
        node_type = str(node.get("type") or "").upper()
        issues.append(
            {
                "nodeKey": source,
                "nodeType": node_type,
                "branchKey": port_key,
                "branchType": "fanOut",
                "code": f"{source}.{port_key}.fanOut",
                "message": f"{source} {port_key} outlet must enable fan-out before connecting multiple downstream nodes",
            }
        )
    return issues


def _validate_reachable_from_start(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> list[dict[str, str]]:
    start_keys = {_node_key(node) for node in nodes if str(node.get("type") or "").upper() == "START" and _node_key(node)}
    if not start_keys:
        return []

    adjacency: dict[str, set[str]] = {}
    for edge in edges:
        source = _node_ref(edge, "source")
        target = _node_ref(edge, "target")
        if source and target:
            adjacency.setdefault(source, set()).add(target)

    reachable: set[str] = set()
    stack = list(start_keys)
    while stack:
        node_key = stack.pop()
        if node_key in reachable:
            continue
        reachable.add(node_key)
        stack.extend(sorted(adjacency.get(node_key, set()) - reachable))

    issues: list[dict[str, str]] = []
    for node in nodes:
        node_key = _node_key(node)
        node_type = str(node.get("type") or "").upper()
        if not node_key or node_type in {"START", "END"} or node_key in reachable:
            continue
        issues.append(
            {
                "nodeKey": node_key,
                "nodeType": node_type,
                "branchKey": "start",
                "branchType": "island",
                "code": f"{node_key}.island",
                "message": f"{node_key} is not reachable from START",
            }
        )
    return issues


def _allows_fan_out(node: Mapping[str, Any], port_key: str) -> bool:
    node_type = str(node.get("type") or "").upper()
    if node_type in {"CONDITION", "INTENT_RECOGNITION"}:
        return True
    if port_key != "default":
        return True
    config = node.get("config") if isinstance(node.get("config"), Mapping) else {}
    if _is_truthy(config.get("allowFanOut") or config.get("allow_fan_out")):
        return True
    for field_name in ("ports", "outputPorts", "output_ports"):
        raw_ports = config.get(field_name)
        if not isinstance(raw_ports, list):
            continue
        for raw_port in raw_ports:
            if not isinstance(raw_port, Mapping):
                continue
            key = str(raw_port.get("key") or raw_port.get("name") or "default").strip() or "default"
            if key == port_key and _is_truthy(raw_port.get("allowFanOut") or raw_port.get("allow_fan_out")):
                return True
    return False


def _is_side_effect_terminal(node: Mapping[str, Any], edges: list[dict[str, Any]]) -> bool:
    node_key = _node_key(node)
    config = node.get("config") if isinstance(node.get("config"), Mapping) else {}
    if _is_truthy(config.get("sideEffectTerminal") or config.get("side_effect_terminal")):
        return True
    return any(
        _node_ref(edge, "target") == node_key
        and _is_truthy(edge.get("sideEffectTerminal") or edge.get("side_effect_terminal"))
        for edge in edges
    )


def _configured_keys(config: Mapping[str, Any], field: str) -> list[str]:
    raw = config.get(field)
    if not isinstance(raw, list):
        return []
    keys: list[str] = []
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            continue
        text = str(item.get("key") or item.get("id") or f"{field}_{index + 1}").strip()
        if text and text not in keys:
            keys.append(text)
    return keys


def _condition_branch_keys(config: Mapping[str, Any]) -> list[str]:
    explicit = _configured_keys(config, "conditionBranches")
    if explicit:
        return explicit
    return _configured_keys(config, "branches")


def _intent_branch_keys(config: Mapping[str, Any]) -> list[str]:
    default_key = str(config.get("defaultIntent") or "default").strip() or "default"
    return [key for key in _configured_keys(config, "intents") if key != default_key]


def _requires_error_branch(node_type: str, config: Mapping[str, Any]) -> bool:
    if node_type not in _ERROR_BRANCH_NODE_TYPES:
        return False
    error_behavior = str(config.get("errorBehavior") or config.get("error_behavior") or "fail").strip().lower()
    return error_behavior == "branch"


def _template_references(value: Any) -> list[tuple[str, str]]:
    references: list[tuple[str, str]] = []
    if isinstance(value, str):
        for match in _TEMPLATE_REF_PATTERN.finditer(value):
            references.append((match.group(1), match.group(2)))
        return references
    if isinstance(value, Mapping):
        for item in value.values():
            references.extend(_template_references(item))
        return references
    if isinstance(value, list):
        for item in value:
            references.extend(_template_references(item))
    return references


def _validate_common_contract(node_key: str, node_type: str, config: Mapping[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    error_behavior = str(config.get("errorBehavior") or config.get("error_behavior") or "fail").strip().lower()
    if error_behavior not in _SUPPORTED_ERROR_BEHAVIORS:
        issues.append(_issue(node_key, node_type, "errorBehavior", f"{node_key} errorBehavior is unsupported: {error_behavior}"))
    for field_name in ("outputParameters", "inputParameters", "inputMappings", "argumentMappings"):
        raw_items = config.get(field_name)
        if isinstance(raw_items, list):
            issues.extend(_validate_parameter_list(node_key, node_type, field_name, raw_items))
    return issues


def _validate_parameter_list(
    node_key: str,
    node_type: str,
    field_name: str,
    raw_items: list[Any],
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for index, item in enumerate(raw_items):
        if not isinstance(item, Mapping):
            issues.append(_issue(node_key, node_type, field_name, f"{node_key} {field_name}[{index}] must be an object"))
            continue
        name = str(item.get("name") or item.get("key") or item.get("target") or item.get("parameter") or "").strip()
        if not name:
            issues.append(_issue(node_key, node_type, field_name, f"{node_key} {field_name}[{index}] name is required"))
        raw_type = item.get("type")
        if raw_type is None or raw_type == "":
            continue
        parameter_type = str(raw_type).strip().lower()
        if parameter_type not in _SUPPORTED_OUTPUT_TYPES:
            label = name or str(index)
            issues.append(
                _issue(
                    node_key,
                    node_type,
                    field_name,
                    f"{node_key} {field_name}.{label} has unsupported type {parameter_type}",
                )
            )
    return issues


def _validate_variable_assign_contract(node_key: str, node_type: str, config: Mapping[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    scope = str(config.get("targetScope") or config.get("scope") or "flow").strip().lower()
    variable_name = str(config.get("targetVariable") or config.get("variable") or "").strip()
    if not variable_name:
        issues.append(_issue(node_key, node_type, "targetVariable", f"{node_key} targetVariable is required"))
    if scope not in _SCOPE_NAMES:
        issues.append(_issue(node_key, node_type, "targetScope", f"{node_key} targetScope is unsupported: {scope}"))
    if scope in _READ_ONLY_SCOPES and variable_name:
        issues.append(_issue(node_key, node_type, "targetScope", f"{node_key} cannot write read-only system variable {scope}.{variable_name}"))
    write_mode = str(config.get("writeMode") or "set").strip().lower()
    if write_mode not in _SUPPORTED_WRITE_MODES:
        issues.append(_issue(node_key, node_type, "writeMode", f"{node_key} writeMode is unsupported: {write_mode}"))
    return issues


def _validate_llm_contract(node_key: str, node_type: str, config: Mapping[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    raw_model_config_id = config.get("modelConfigId") or config.get("model_config_id")
    if raw_model_config_id not in (None, "") and not _is_optional_int(raw_model_config_id):
        issues.append(_issue(node_key, node_type, "modelConfigId", f"{node_key} modelConfigId must be numeric"))
    return issues


def _validate_api_call_contract(node_key: str, node_type: str, config: Mapping[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    resource_id = str(config.get("resourceId") or config.get("resource_id") or "").strip()
    if not resource_id:
        issues.append(_issue(node_key, node_type, "resourceId", f"{node_key} resourceId is required"))
    elif not (resource_id.startswith("api-resource:") or _is_optional_int(resource_id)):
        issues.append(_issue(node_key, node_type, "resourceId", f"{node_key} resourceId must reference an API resource"))
    issues.extend(_validate_timeout_retry_policy(node_key, node_type, config))
    return issues


def _validate_tool_call_contract(node_key: str, node_type: str, config: Mapping[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    resource_type = str(config.get("resourceType") or config.get("resource_type") or config.get("type") or "MCP_TOOL")
    resource_type = resource_type.strip().upper().replace("-", "_")
    if resource_type not in {"MCP_TOOL", "API_TOOL", "API_RESOURCE"}:
        issues.append(_issue(node_key, node_type, "resourceType", f"{node_key} resourceType is unsupported: {resource_type}"))
    resource_id = str(config.get("resourceId") or config.get("resource_id") or "").strip()
    if not resource_id:
        issues.append(_issue(node_key, node_type, "resourceId", f"{node_key} resourceId is required"))
    tool_name = str(config.get("toolName") or config.get("tool_name") or config.get("name") or "").strip()
    if not tool_name:
        issues.append(_issue(node_key, node_type, "toolName", f"{node_key} toolName is required"))
    if resource_type == "MCP_TOOL" and not _has_server_ids(config):
        issues.append(_issue(node_key, node_type, "serverIds", f"{node_key} serverIds is required"))
    if tool_name and _is_write_capable_tool(tool_name) and not _is_truthy(config.get("allowWrite") or config.get("allow_write")):
        issues.append(_issue(node_key, node_type, "allowWrite", f"{node_key} write-capable tool requires allowWrite"))
    issues.extend(_validate_timeout_retry_policy(node_key, node_type, config))
    return issues


def _validate_timeout_retry_policy(node_key: str, node_type: str, config: Mapping[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    timeout_ms = config.get("timeoutMs") if "timeoutMs" in config else config.get("timeout_ms")
    if timeout_ms not in (None, "") and (not _is_optional_int(timeout_ms) or int(timeout_ms) <= 0):
        issues.append(_issue(node_key, node_type, "timeoutMs", f"{node_key} timeoutMs must be a positive integer"))
    retry_count = config.get("retryCount") if "retryCount" in config else config.get("retry_count")
    if retry_count not in (None, "") and (not _is_optional_int(retry_count) or int(retry_count) < 0):
        issues.append(_issue(node_key, node_type, "retryCount", f"{node_key} retryCount must be a non-negative integer"))
    return issues


def _has_server_ids(config: Mapping[str, Any]) -> bool:
    server_ids = config.get("serverIds") if "serverIds" in config else config.get("server_ids")
    if isinstance(server_ids, list):
        return any(_is_optional_int(item) for item in server_ids)
    raw_server_id = config.get("serverId") if "serverId" in config else config.get("server_id")
    return raw_server_id not in (None, "") and _is_optional_int(raw_server_id)


def _is_write_capable_tool(tool_name: str) -> bool:
    normalized = tool_name.strip().lower()
    return normalized.startswith(("create_", "update_", "delete_", "remove_", "write_"))


def _is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _is_optional_int(value: Any) -> bool:
    try:
        int(value)
    except (TypeError, ValueError):
        return False
    return True


def _issue(node_key: str, node_type: str, code: str, message: str) -> dict[str, str]:
    return {
        "nodeKey": node_key,
        "nodeType": node_type,
        "code": f"{node_key}.{code}",
        "message": message,
    }
