from __future__ import annotations

import ast
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Protocol

from app.modules.knowledge.api.facade import KnowledgeFacade
from app.modules.workflow.domain.context import ExecutionContext
from app.modules.workflow.infra.repository import WorkflowRepository

MAX_STEPS = 50
_LOCAL_TEMPLATE_PATTERN = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")


class WorkflowExecutionError(Exception):
    pass


@dataclass(frozen=True)
class WorkflowExecutionResult:
    run_id: int
    status: str
    output: dict[str, Any]


class NodeExecutor(Protocol):
    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        ...


class WorkflowLlmCompleter(Protocol):
    def complete_prompt(self, prompt: str) -> str:
        ...


class StartNodeExecutor:
    def __init__(self, input_data: dict[str, Any]) -> None:
        self._input_data = input_data

    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        return dict(self._input_data)


class LlmNodeExecutor:
    def __init__(self, completer: WorkflowLlmCompleter | None = None) -> None:
        self._completer = completer

    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        output_variable = str(config.get("outputVariable") or "answer")
        prompt = context.render(str(config.get("prompt") or ""))
        if self._completer is not None:
            return {output_variable: self._completer.complete_prompt(prompt)}
        return {output_variable: f"LLM mock: {prompt}"}


class ApiCallNodeExecutor:
    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        output_variable = str(config.get("outputVariable") or "response")
        method = str(config.get("method") or "GET").upper()
        url = context.render(str(config.get("url") or config.get("endpoint") or ""))
        return {output_variable: f"API mock: {method} {url}".strip()}


class KnowledgeNodeExecutor:
    def __init__(self, knowledge_facade: KnowledgeFacade | None = None) -> None:
        self._knowledge_facade = knowledge_facade

    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        output_variable = str(config.get("outputVariable") or "answer")
        query = context.render(str(config.get("query") or ""))
        knowledge_base_id = config.get("knowledgeBaseId") or config.get("knowledge_base_id")
        if self._knowledge_facade is None or knowledge_base_id is None:
            return {output_variable: f"Knowledge mock: {query}"}
        results = self._knowledge_facade.search_chunks(int(knowledge_base_id), query, top_k=1)
        content = results[0].content if results else ""
        return {output_variable: content}


class ConditionNodeExecutor:
    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        output_variable = str(config.get("outputVariable") or "route")
        expression = context.render(str(config.get("expression") or ""))
        return {output_variable: expression}


class EndNodeExecutor:
    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        declared_output = _declared_end_output(config, context)
        has_declared_output = isinstance(config.get("outputParameters"), list)
        return_mode = str(config.get("returnMode") or "").lower()
        variable_return_mode = return_mode in {"variables", "返回变量"}
        output_variable = str(config.get("outputVariable") or next(iter(declared_output), "output") or "output")
        if "output" in config and not variable_return_mode:
            rendered_output = _render_local_template(context.render(str(config["output"])), declared_output)
            return {output_variable: rendered_output}
        if declared_output or has_declared_output:
            return declared_output
        return {output_variable: context.find_value(output_variable)}




class CodeNodeExecutor:
    _safe_builtins = {
        "abs": abs,
        "all": all,
        "any": any,
        "bool": bool,
        "dict": dict,
        "float": float,
        "int": int,
        "len": len,
        "list": list,
        "max": max,
        "min": min,
        "round": round,
        "sorted": sorted,
        "str": str,
        "sum": sum,
        "tuple": tuple,
    }
    _blocked_call_names = {"__import__", "open", "eval", "exec", "compile", "input", "globals", "locals", "vars"}
    _blocked_nodes = (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal)

    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        language = str(config.get("language") or "python").lower()
        if language not in {"python", "python3"}:
            raise WorkflowExecutionError(f"Unsupported CODE language: {language}")
        code = str(config.get("code") or config.get("body") or "").strip()
        if not code:
            raise WorkflowExecutionError("CODE node requires code")
        tree = _validated_code_tree(code)
        inputs = _node_inputs(config, context)
        local_vars: dict[str, Any] = {"inputs": inputs, "result": None}
        exec(  # noqa: S102 - deliberate restricted workflow node sandbox.
            compile(tree, "<workflow-code-node>", "exec"),
            {"__builtins__": self._safe_builtins, "json": json, "re": re},
            local_vars,
        )
        result = local_vars.get("result")
        if result is None:
            result = local_vars.get("output")
        if not isinstance(result, Mapping):
            output_variable = str(config.get("outputVariable") or "output")
            return {output_variable: result}
        return _declared_output(dict(result), config)


class TextProcessNodeExecutor:
    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        operation = str(config.get("operation") or "format_template").lower()
        output_variable = _first_output_name(config, str(config.get("outputVariable") or "text"))
        if operation in {"format_template", "template", "format"}:
            value = context.render(str(config.get("template") or config.get("source") or ""))
            return {output_variable: value}
        if operation in {"concatenate", "concat"}:
            parts = config.get("parts") or config.get("texts") or []
            if not isinstance(parts, list):
                parts = [parts]
            separator = context.render(str(config.get("separator") or ""))
            value = separator.join(context.render(str(part)) for part in parts)
            return {output_variable: value}
        if operation in {"extract_regex", "regex_extract", "extract"}:
            source = context.render(str(config.get("source") or config.get("text") or ""))
            pattern = str(config.get("pattern") or "")
            if not pattern:
                raise WorkflowExecutionError("TEXT_PROCESS regex extraction requires pattern")
            match = re.search(pattern, source)
            group = config.get("group", 0)
            try:
                extracted = match.group(group) if match else ""
            except IndexError as exc:
                raise WorkflowExecutionError(f"TEXT_PROCESS regex group not found: {group}") from exc
            return {output_variable: extracted, "matched": match is not None, "groups": list(match.groups()) if match else []}
        if operation == "replace":
            source = context.render(str(config.get("source") or config.get("text") or ""))
            pattern = str(config.get("pattern") or config.get("search") or "")
            replacement = context.render(str(config.get("replacement") or ""))
            return {output_variable: re.sub(pattern, replacement, source) if pattern else source}
        if operation == "trim":
            source = context.render(str(config.get("source") or config.get("text") or ""))
            return {output_variable: source.strip()}
        raise WorkflowExecutionError(f"Unsupported TEXT_PROCESS operation: {operation}")


class JsonParseNodeExecutor:
    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        output_variable = _first_output_name(config, str(config.get("outputVariable") or "parsed"))
        source = _source_value(config, context)
        if isinstance(source, str):
            try:
                parsed = json.loads(source)
            except json.JSONDecodeError as exc:
                return {output_variable: None, "parsed": None, "parseStatus": "FAILED", "errorMessage": exc.msg}
        else:
            parsed = source
        output = {output_variable: parsed, "parsed": parsed, "parseStatus": "SUCCEEDED", "errorMessage": ""}
        for item in _field_map(config):
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            output[name] = _json_path_value(parsed, str(item.get("path") or item.get("source") or ""))
        return output


class VariableAggregationNodeExecutor:
    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        groups = _aggregation_groups(config, context)
        if groups:
            output: dict[str, Any] = {}
            source_status: list[dict[str, Any]] = []
            for group in groups:
                name = group["name"]
                variables = group["variables"]
                output[name] = next((item["value"] for item in variables if _not_empty(item["value"])), None)
                source_status.append(
                    {
                        "name": name,
                        "empty": not _not_empty(output[name]),
                        "variables": [
                            {"empty": not _not_empty(item["value"])}
                            for item in variables
                        ],
                    },
                )
            output["sourceStatus"] = source_status
            return output

        output_variable = _first_output_name(config, str(config.get("outputVariable") or "aggregate"))
        sources = _aggregation_sources(config, context)
        strategy = str(config.get("strategy") or config.get("mergeStrategy") or "first_non_empty").lower()
        default_value = _render_optional(config.get("defaultValue"), context)

        if strategy in {"first_non_empty", "first", "coalesce"}:
            value = next((source["value"] for source in sources if _not_empty(source["value"])), default_value)
        elif strategy in {"last_non_empty", "last"}:
            value = next((source["value"] for source in reversed(sources) if _not_empty(source["value"])), default_value)
        elif strategy in {"concat", "concatenate"}:
            separator = context.render(str(config.get("separator") or ""))
            value = separator.join(str(source["value"]) for source in sources if _not_empty(source["value"]))
            if value == "" and default_value is not None:
                value = default_value
        elif strategy in {"array", "list"}:
            value = [source["value"] for source in sources if _not_empty(source["value"])]
            if not value and default_value is not None:
                value = default_value
        elif strategy in {"object_merge", "merge_object"}:
            merged: dict[str, Any] = {}
            for source in sources:
                if isinstance(source["value"], Mapping):
                    merged.update(source["value"])
                elif source["name"] and _not_empty(source["value"]):
                    merged[str(source["name"])] = source["value"]
            value = merged or default_value
        else:
            raise WorkflowExecutionError(f"Unsupported VARIABLE_AGGREGATION strategy: {strategy}")

        return {
            output_variable: value,
            "sourceStatus": [
                {"name": source["name"], "empty": not _not_empty(source["value"])}
                for source in sources
            ],
        }


class VariableAssignNodeExecutor:
    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        scope = str(config.get("targetScope") or config.get("scope") or "flow").strip().lower()
        variable_name = str(config.get("targetVariable") or config.get("variable") or "").strip()
        if not variable_name:
            raise WorkflowExecutionError("VARIABLE_ASSIGN requires targetVariable")
        write_mode = str(config.get("writeMode") or "set").strip().lower()
        if write_mode not in {"set", "append", "clear"}:
            raise WorkflowExecutionError(f"Unsupported VARIABLE_ASSIGN writeMode: {write_mode}")
        value = _assignment_source_value(config, context, scope, variable_name)
        try:
            written_value = context.set_scope_value(scope, variable_name, value, write_mode)
        except ValueError as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        output_variable = _first_output_name(config, str(config.get("outputVariable") or "assigned"))
        return {
            output_variable: written_value,
            "assigned": write_mode != "clear",
            "scope": scope,
            "variable": variable_name,
            "value": written_value,
        }


class ConditionBranchPicker:
    def pick(self, node_key: str, edges: list[dict[str, Any]], branch_value: str) -> str | None:
        source_edges = [edge for edge in edges if edge["source_node_key"] == node_key]
        matched = next(
            (
                edge
                for edge in source_edges
                if edge.get("condition_expr") is not None and str(edge["condition_expr"]) == branch_value
            ),
            None,
        )
        if matched:
            return str(matched["target_node_key"])
        default = next((edge for edge in source_edges if not edge.get("condition_expr")), None)
        return str(default["target_node_key"]) if default else None


class WorkflowExecutionEngine:
    def __init__(
        self,
        repository: WorkflowRepository,
        knowledge_facade: KnowledgeFacade | None = None,
        llm_completer: WorkflowLlmCompleter | None = None,
    ) -> None:
        self._repository = repository
        self._knowledge_facade = knowledge_facade
        self._llm_completer = llm_completer

    def run(self, workflow_id: int, input_data: dict[str, Any]) -> WorkflowExecutionResult:
        workflow = self._repository.get(workflow_id)
        if workflow is None:
            raise WorkflowExecutionError("Workflow not found")
        nodes = self._repository.list_nodes(workflow_id)
        edges = self._repository.list_edges(workflow_id)
        run_id = self._repository.create_run(workflow_id, input_data)
        try:
            output = self._run_graph(run_id, nodes, edges, input_data)
            self._repository.finish_run(run_id, "SUCCEEDED", output=output)
            return WorkflowExecutionResult(run_id=run_id, status="SUCCEEDED", output=output)
        except Exception as exc:
            self._repository.finish_run(run_id, "FAILED", output={}, error=str(exc))
            raise

    def _run_graph(
        self,
        run_id: int,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        node_map = {str(node["node_key"]): node for node in nodes}
        current = next((node for node in nodes if node["type"] == "START"), None)
        if current is None:
            raise WorkflowExecutionError("Workflow START node not found")

        context = ExecutionContext()
        for _step in range(MAX_STEPS):
            node_run_id = self._repository.create_node_run(run_id, str(current["node_key"]), str(current["type"]))
            started_at = perf_counter()
            try:
                output = self._execute_node(current, context, input_data)
                context.set_output(str(current["node_key"]), output)
                elapsed_ms = int((perf_counter() - started_at) * 1000)
                self._repository.finish_node_run(node_run_id, "SUCCEEDED", outputs=output, elapsed_ms=elapsed_ms)
            except Exception as exc:
                elapsed_ms = int((perf_counter() - started_at) * 1000)
                self._repository.finish_node_run(node_run_id, "FAILED", outputs={}, error=str(exc), elapsed_ms=elapsed_ms)
                raise

            if current["type"] == "END":
                return output

            next_node_key = self._next_node_key(current, edges, output)
            if next_node_key is None or next_node_key not in node_map:
                raise WorkflowExecutionError(f"Next node not found after {current['node_key']}")
            current = node_map[next_node_key]

        raise WorkflowExecutionError("Workflow step limit exceeded")

    def _execute_node(
        self,
        node: dict[str, Any],
        context: ExecutionContext,
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        node_type = str(node["type"])
        if node_type == "START":
            return StartNodeExecutor(input_data).execute(node, context)
        if node_type == "LLM":
            return LlmNodeExecutor(self._llm_completer).execute(node, context)
        if node_type == "API_CALL":
            return ApiCallNodeExecutor().execute(node, context)
        if node_type == "KNOWLEDGE":
            return KnowledgeNodeExecutor(self._knowledge_facade).execute(node, context)
        if node_type == "CONDITION":
            return ConditionNodeExecutor().execute(node, context)
        if node_type == "CODE":
            return CodeNodeExecutor().execute(node, context)
        if node_type == "TEXT_PROCESS":
            return TextProcessNodeExecutor().execute(node, context)
        if node_type == "JSON_PARSE":
            return JsonParseNodeExecutor().execute(node, context)
        if node_type == "VARIABLE_AGGREGATION":
            return VariableAggregationNodeExecutor().execute(node, context)
        if node_type == "VARIABLE_ASSIGN":
            return VariableAssignNodeExecutor().execute(node, context)
        if node_type == "END":
            return EndNodeExecutor().execute(node, context)
        raise WorkflowExecutionError(f"Unknown node type: {node_type}")

    def _next_node_key(
        self,
        node: dict[str, Any],
        edges: list[dict[str, Any]],
        output: dict[str, Any],
    ) -> str | None:
        node_key = str(node["node_key"])
        if node["type"] == "CONDITION":
            branch_value = str(next(iter(output.values()), ""))
            return ConditionBranchPicker().pick(node_key, edges, branch_value)
        edge = next(
            (
                item
                for item in edges
                if item["source_node_key"] == node_key and not item.get("condition_expr")
            ),
            None,
        )
        return str(edge["target_node_key"]) if edge else None


def _config(node: dict[str, Any]) -> dict[str, Any]:
    config = node.get("config")
    return dict(config) if isinstance(config, dict) else {}



def _first_output_name(config: dict[str, Any], fallback: str) -> str:
    parameters = config.get("outputParameters")
    if isinstance(parameters, list):
        first = next((item for item in parameters if isinstance(item, Mapping) and str(item.get("name") or "").strip()), None)
        if first is not None:
            return str(first["name"]).strip()
    return fallback


def _source_value(config: dict[str, Any], context: ExecutionContext) -> Any:
    if "source" in config:
        value = config["source"]
    elif "value" in config:
        value = config["value"]
    elif "input" in config:
        value = config["input"]
    else:
        value = ""
    return context.render(value) if isinstance(value, str) else value


def _assignment_source_value(
    config: dict[str, Any],
    context: ExecutionContext,
    scope: str,
    variable_name: str,
) -> Any:
    mode = str(config.get("sourceValueMode") or config.get("valueMode") or config.get("assignmentMode") or "").strip().lower()
    if mode in {"operation", "calculation", "compute", "operator"}:
        return _assignment_operation_value(config, context, scope, variable_name)
    return _source_value(config, context)


def _assignment_operation_value(
    config: dict[str, Any],
    context: ExecutionContext,
    scope: str,
    variable_name: str,
) -> int | float:
    operation = str(config.get("operation") or config.get("operator") or "add").strip().lower()
    raw_operand = config.get("operand")
    if raw_operand is None:
        raw_operand = config.get("source")
    if raw_operand is None:
        raw_operand = 1 if operation in {"increment", "inc", "decrement", "dec"} else 0
    operand = context.render(raw_operand) if isinstance(raw_operand, str) else raw_operand
    current = context.get_scope(scope).get(variable_name, 0)
    current_number = _assignment_number(current, f"{scope}.{variable_name}")
    operand_number = _assignment_number(operand, "operand")

    if operation in {"add", "plus", "increment", "inc"}:
        return _normalized_assignment_number(current_number + operand_number)
    if operation in {"subtract", "minus", "decrement", "dec"}:
        return _normalized_assignment_number(current_number - operand_number)
    if operation in {"multiply", "mul", "times"}:
        return _normalized_assignment_number(current_number * operand_number)
    if operation in {"divide", "div"}:
        if operand_number == 0:
            raise WorkflowExecutionError("VARIABLE_ASSIGN operation divide requires non-zero operand")
        return _normalized_assignment_number(current_number / operand_number)
    raise WorkflowExecutionError(f"Unsupported VARIABLE_ASSIGN operation: {operation}")


def _assignment_number(value: Any, label: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise WorkflowExecutionError(f"VARIABLE_ASSIGN operation requires numeric {label}: {value}") from exc


def _normalized_assignment_number(value: float) -> int | float:
    return int(value) if value.is_integer() else value


def _aggregation_sources(config: dict[str, Any], context: ExecutionContext) -> list[dict[str, Any]]:
    raw = config.get("sources") or config.get("inputSources") or []
    if not isinstance(raw, list):
        return []
    result: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("name") or item.get("label") or "").strip()
        value = item.get("value")
        if isinstance(value, str):
            value = context.render(value)
        result.append({"name": name, "value": value})
    return result



def _aggregation_groups(config: dict[str, Any], context: ExecutionContext) -> list[dict[str, Any]]:
    raw = config.get("groups") or config.get("mergeGroups")
    inputs = config.get("inputs")
    if raw is None and isinstance(inputs, Mapping):
        raw = inputs.get("mergeGroups")
    if not isinstance(raw, list):
        return []
    result: list[dict[str, Any]] = []
    for group_index, group in enumerate(raw):
        if not isinstance(group, Mapping):
            continue
        name = str(group.get("name") or group.get("groupName") or f"Group{group_index + 1}").strip()
        if not name:
            continue
        raw_variables = group.get("variables") or group.get("values") or []
        if not isinstance(raw_variables, list):
            raw_variables = []
        variables: list[dict[str, Any]] = []
        for item in raw_variables:
            value = item
            if isinstance(item, Mapping):
                value = item.get("value")
            if isinstance(value, str):
                value = context.render(value)
            variables.append({"value": value})
        result.append({"name": name, "variables": variables})
    return result


def _render_optional(value: Any, context: ExecutionContext) -> Any:
    if value is None:
        return None
    return context.render(value) if isinstance(value, str) else value


def _not_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value != ""
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) > 0
    return True



def _validated_code_tree(code: str) -> ast.Module:
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        raise WorkflowExecutionError(f"CODE syntax error: {exc.msg}") from exc
    for node in ast.walk(tree):
        if isinstance(node, CodeNodeExecutor._blocked_nodes):
            raise WorkflowExecutionError("CODE node contains unsupported syntax")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in CodeNodeExecutor._blocked_call_names:
                raise WorkflowExecutionError(f"CODE node cannot call {node.func.id}")
            if isinstance(node.func, ast.Attribute) and node.func.attr.startswith("__"):
                raise WorkflowExecutionError("CODE node cannot call private attributes")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise WorkflowExecutionError("CODE node cannot access private attributes")
    return tree


def _node_inputs(config: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
    inputs = context.get_output("start")
    parameters = config.get("inputParameters") or config.get("inputs") or []
    if not isinstance(parameters, list):
        return inputs
    mapped: dict[str, Any] = {}
    for item in parameters:
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("name") or item.get("key") or "").strip()
        if not name:
            continue
        value = item.get("value")
        if isinstance(value, str):
            mapped[name] = context.render(value)
        elif value is not None:
            mapped[name] = value
        else:
            mapped[name] = inputs.get(name, "")
    return mapped or inputs


def _declared_output(values: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    parameters = config.get("outputParameters")
    if not isinstance(parameters, list):
        return values
    output: dict[str, Any] = {}
    for item in parameters:
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("name") or "").strip()
        if name:
            output[name] = values.get(name)
    return output or values


def _declared_end_output(config: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
    parameters = config.get("outputParameters")
    if not isinstance(parameters, list):
        return {}
    output: dict[str, Any] = {}
    for item in parameters:
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        if "value" in item or "valueMode" in item:
            value = item.get("value")
            if str(item.get("valueMode") or "reference") == "literal":
                output[name] = value
            else:
                output[name] = context.render(str(value or ""))
        else:
            output[name] = context.find_value(name)
    return output


def _render_local_template(template: str, values: Mapping[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        value = values.get(match.group(1))
        return "" if value is None else str(value)

    return _LOCAL_TEMPLATE_PATTERN.sub(replace, template)


def _field_map(config: dict[str, Any]) -> list[dict[str, Any]]:
    raw = config.get("fieldMap") or config.get("mappings") or []
    if not isinstance(raw, list):
        return []
    return [dict(item) for item in raw if isinstance(item, Mapping)]


def _json_path_value(value: Any, path: str) -> Any:
    if path in {"", "$"}:
        return value
    current = value
    tokens = path[2:].split(".") if path.startswith("$.") else path.split(".")
    for token in tokens:
        if token == "":
            continue
        if isinstance(current, Mapping):
            current = current.get(token)
            continue
        if isinstance(current, list):
            try:
                current = current[int(token)]
            except (ValueError, IndexError):
                return None
            continue
        return None
    return current
