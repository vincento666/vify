from __future__ import annotations

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


class StartNodeExecutor:
    def __init__(self, input_data: dict[str, Any]) -> None:
        self._input_data = input_data

    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        return dict(self._input_data)


class LlmNodeExecutor:
    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        output_variable = str(config.get("outputVariable") or "answer")
        prompt = context.render(str(config.get("prompt") or ""))
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
    ) -> None:
        self._repository = repository
        self._knowledge_facade = knowledge_facade

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
            return LlmNodeExecutor().execute(node, context)
        if node_type == "API_CALL":
            return ApiCallNodeExecutor().execute(node, context)
        if node_type == "KNOWLEDGE":
            return KnowledgeNodeExecutor(self._knowledge_facade).execute(node, context)
        if node_type == "CONDITION":
            return ConditionNodeExecutor().execute(node, context)
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
