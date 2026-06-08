from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Protocol

from app.modules.knowledge.api.facade import KnowledgeFacade
from app.modules.workflow.domain.context import ExecutionContext
from app.modules.workflow.infra.repository import WorkflowRepository

MAX_STEPS = 50


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
        output_variable = str(config.get("outputVariable") or "output")
        if "output" in config:
            return {output_variable: context.render(str(config["output"]))}
        return {output_variable: context.find_value(output_variable)}



class VariableAggregationNodeExecutor:
    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
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
        value = _source_value(config, context)
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
