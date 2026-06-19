from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from app.core.errors import BizError, ErrorCode
from app.modules.knowledge.api.facade import KnowledgeFacade
from app.modules.workflow.domain.context import ExecutionContext
from app.modules.workflow.domain.engine import (
    AgentCallNodeExecutor,
    AgentInvocationFacade,
    ApiCallNodeExecutor,
    ApiToolExecutor,
    CodeNodeExecutor,
    ConditionBranchPicker,
    ConditionNodeExecutor,
    EndNodeExecutor,
    ExecuteWorkflowNodeExecutor,
    HumanInputNodeExecutor,
    InformationCollectionNodeExecutor,
    IntentRecognitionNodeExecutor,
    JsonParseNodeExecutor,
    KnowledgeNodeExecutor,
    LlmNodeExecutor,
    TextProcessNodeExecutor,
    ToolCallNodeExecutor,
    VariableAggregationNodeExecutor,
    VariableAssignNodeExecutor,
    WorkflowInterrupt,
    WorkflowLlmCompleter,
)
from app.modules.chat.domain.tool_runner import McpToolExecutor
from app.modules.workflow.domain.graph_validation import (
    validate_node_contracts,
    validate_node_endpoints,
    validate_variable_references,
)
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.publish_repository import WorkflowPublishRepository
from app.modules.workflow.infra.repository import WorkflowRepository
from app.modules.workflow.web.schemas import format_datetime


_SECRET_KEYS = {"api_key", "apikey", "authorization", "password", "secret", "token", "credential", "credentials"}
_SUPPORTED_CORE_NODE_TYPES = {
    "START",
    "MESSAGE",
    "QUESTION",
    "HUMAN_INPUT",
    "LLM",
    "CODE",
    "TEXT_PROCESS",
    "JSON_PARSE",
    "VARIABLE_ASSIGN",
    "VARIABLE_AGGREGATION",
    "CONDITION",
    "INTENT_RECOGNITION",
    "INFORMATION_COLLECTION",
    "KNOWLEDGE",
    "API_CALL",
    "TOOL_CALL",
    "EXECUTE_WORKFLOW",
    "TRANSFER_TO_HUMAN",
    "AGENT_CALL",
    "END",
}
_RUNTIME_V2_CANCELLABLE_STATUSES = {"RUNNING", "INTERRUPTED"}
_RUNTIME_V2_TERMINAL_STATUSES = {"SUCCEEDED", "FAILED", "CANCELLED"}
_RUNTIME_V2_ERROR_POLICY_NODE_TYPES = {"LLM", "API_CALL", "TOOL_CALL", "CODE", "EXECUTE_WORKFLOW", "AGENT_CALL"}
RuntimeV2LlmCompleterResolver = Callable[[int], WorkflowLlmCompleter | None]
RuntimeV2AgentInvokerResolver = Callable[[int], AgentInvocationFacade | None]


class RuntimeV2RefBuilder:
    @staticmethod
    def build(*, owner_type: str, owner_id: int, run_id: int) -> dict[str, Any]:
        normalized_owner = owner_type.upper()
        if normalized_owner not in {"WORKFLOW", "CHATFLOW"}:
            raise ValueError(f"Unsupported runtime v2 owner type: {owner_type}")
        return {
            "ownerType": normalized_owner,
            "ownerId": owner_id,
            "runId": run_id,
            "statusRef": f"/api/v1/runtime-runs/{run_id}",
            "eventsRef": f"/api/v1/runtime-runs/{run_id}/events",
            "eventStreamRef": f"/api/v1/runtime-runs/{run_id}/events/stream?afterSequence=0",
            "nodesRef": f"/api/v1/runtime-runs/{run_id}/nodes",
            "resultRef": f"/api/v1/runtime-runs/{run_id}/result",
        }


class RuntimeV2CompatibilityChecker:
    @staticmethod
    def check(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, Any]:
        unsupported_nodes: list[dict[str, str]] = []
        node_types_by_key: dict[str, str] = {}
        node_configs_by_key: dict[str, dict[str, Any]] = {}
        for node in nodes:
            node_type = str(node.get("type") or "").upper()
            node_key = str(node.get("nodeKey") or node.get("node_key") or "")
            node_types_by_key[node_key] = node_type
            node_configs_by_key[node_key] = dict(node.get("config") or {})
            if node_type not in _SUPPORTED_CORE_NODE_TYPES:
                unsupported_nodes.append(
                    {
                        "nodeKey": node_key,
                        "nodeType": node_type,
                    }
                )
                continue
            config = dict(node.get("config") or {})
            if node_type == "API_CALL":
                reason = _runtime_v2_api_call_unsupported_reason(config)
                if reason:
                    unsupported_nodes.append({"nodeKey": node_key, "nodeType": node_type, "reason": reason})
            if node_type == "TOOL_CALL":
                reason = _runtime_v2_tool_call_unsupported_reason(config)
                if reason:
                    unsupported_nodes.append({"nodeKey": node_key, "nodeType": node_type, "reason": reason})
            if node_type == "INFORMATION_COLLECTION" and _requires_llm_information_collection(dict(node.get("config") or {})):
                unsupported_nodes.append(
                    {
                        "nodeKey": node_key,
                        "nodeType": node_type,
                        "reason": "llm_dependent_information_collection",
                    }
                )
        unsupported_patterns: list[str] = []
        outgoing_counts: dict[str, int] = {}
        for edge in edges:
            source = str(edge.get("sourceNodeKey") or edge.get("source_node_key") or "")
            outgoing_counts[source] = outgoing_counts.get(source, 0) + 1
        for source, count in outgoing_counts.items():
            source_type = node_types_by_key.get(source)
            source_config = node_configs_by_key.get(source, {})
            if (
                count > 1
                and source_type not in {"CONDITION", "INTENT_RECOGNITION"}
                and not _runtime_v2_allows_error_branching(str(source_type or ""), source_config)
            ):
                if "branching_edges" not in unsupported_patterns:
                    unsupported_patterns.append("branching_edges")
        endpoint_issues = validate_node_endpoints(nodes, edges)
        contract_issues = validate_node_contracts(nodes)
        reference_issues = validate_variable_references(nodes)
        validation_issues = [*endpoint_issues, *contract_issues, *reference_issues]
        branch_validation_errors = [issue["code"] for issue in validation_issues]
        has_branch_endpoint_issue = any(issue["nodeType"] in {"CONDITION", "INTENT_RECOGNITION"} for issue in endpoint_issues)
        has_regular_endpoint_issue = any(issue["nodeType"] not in {"CONDITION", "INTENT_RECOGNITION"} for issue in endpoint_issues)
        if has_branch_endpoint_issue and "branch_edges_incomplete" not in unsupported_patterns:
            unsupported_patterns.append("branch_edges_incomplete")
        if has_regular_endpoint_issue and "node_endpoints_incomplete" not in unsupported_patterns:
            unsupported_patterns.append("node_endpoints_incomplete")
        if contract_issues and "node_contract_invalid" not in unsupported_patterns:
            unsupported_patterns.append("node_contract_invalid")
        if reference_issues and "variable_references_invalid" not in unsupported_patterns:
            unsupported_patterns.append("variable_references_invalid")
        supported = not unsupported_nodes and not unsupported_patterns and not branch_validation_errors
        return {
            "supported": supported,
            "fallbackScope": "" if supported else "whole_graph",
            "unsupportedNodes": unsupported_nodes,
            "unsupportedPatterns": unsupported_patterns,
            "branchValidationErrors": branch_validation_errors,
            "supportedNodeTypes": sorted(_SUPPORTED_CORE_NODE_TYPES),
        }


@dataclass(frozen=True)
class RuntimeV2Start:
    run_id: int
    owner_type: str
    owner_id: int
    chatflow_id: int
    session_id: str
    status: str
    event_stream_ref: str
    events_ref: str
    result_ref: str
    version_id: int | None = None
    version: int | None = None


class ChatflowRuntimeV2Service:
    def __init__(
        self,
        repository: WorkflowRepository,
        state_repository: ChatflowStateRepository,
        *,
        completion_delay_seconds: float = 0.45,
        owner_type: str = "CHATFLOW",
        flow_type: str = "CHATFLOW",
        use_chatflow_session: bool = True,
        publish_repository: WorkflowPublishRepository | None = None,
        knowledge_facade: KnowledgeFacade | None = None,
        llm_completer: WorkflowLlmCompleter | None = None,
        llm_completer_resolver: RuntimeV2LlmCompleterResolver | None = None,
        agent_invoker_resolver: RuntimeV2AgentInvokerResolver | None = None,
        mcp_tool_executor: McpToolExecutor | None = None,
        api_tool_executor: ApiToolExecutor | None = None,
    ) -> None:
        self._repository = repository
        self._state_repository = state_repository
        self._completion_delay_seconds = completion_delay_seconds
        self._owner_type = owner_type.upper()
        self._flow_type = flow_type.upper()
        self._use_chatflow_session = use_chatflow_session
        self._publish_repository = publish_repository
        self._knowledge_facade = knowledge_facade
        self._llm_completer = llm_completer
        self._llm_completer_resolver = llm_completer_resolver
        self._agent_invoker_resolver = agent_invoker_resolver
        self._mcp_tool_executor = mcp_tool_executor
        self._api_tool_executor = api_tool_executor
        self._llm_completer_cache: dict[int, WorkflowLlmCompleter | None] = {}
        self._agent_invoker_cache: dict[int, AgentInvocationFacade | None] = {}

    def start_run(
        self,
        chatflow_id: int,
        input_data: dict[str, Any],
        idempotency_key: str | None = None,
        version_id: int | None = None,
    ) -> dict[str, Any]:
        self._ensure_owner(chatflow_id)
        if idempotency_key:
            replay_event = self._state_repository.find_started_run_by_idempotency_key(chatflow_id, idempotency_key)
            if replay_event is not None:
                payload = dict(replay_event.get("payload") or {})
                run_id = int(payload.get("runId") or replay_event["run_id"])
                run = self._run_or_404(run_id)
                replay_payload = _start_payload(
                    RuntimeV2Start(
                        run_id=run_id,
                        owner_type=str(payload.get("ownerType") or self._owner_type),
                        owner_id=chatflow_id,
                        chatflow_id=chatflow_id,
                        session_id=str(replay_event["session_id"]),
                        status=str(run["status"]),
                        event_stream_ref=f"/api/v1/runtime-runs/{run_id}/events/stream?afterSequence=0",
                        events_ref=f"/api/v1/runtime-runs/{run_id}/events",
                        result_ref=f"/api/v1/runtime-runs/{run_id}/result",
                        version_id=_optional_int(payload.get("versionId")),
                        version=_optional_int(payload.get("version")),
                    )
                )
                replay_payload["idempotentReplay"] = True
                return replay_payload
        definition = self._definition_for_start(chatflow_id, version_id)
        compatibility = RuntimeV2CompatibilityChecker.check(definition["nodes"], definition["edges"])
        if not compatibility["supported"]:
            raise BizError(ErrorCode.BAD_REQUEST, f"Unsupported runtime v2 graph: {compatibility}")
        persisted_input = _with_runtime_metadata(input_data, self._owner_type, definition)
        run_id = self._repository.create_run(chatflow_id, persisted_input)
        session_id = str(input_data.get("sys.session_id") or f"{self._owner_type.lower()}-v2-{run_id}")
        if self._use_chatflow_session:
            self._state_repository.create_session(
                session_id=session_id,
                chatflow_id=chatflow_id,
                conversation_id=str(input_data.get("sys.conversation_id") or session_id),
                user_id=str(input_data.get("sys.user_id") or ""),
                channel=str(input_data.get("sys.channel") or "api"),
                channel_id=str(input_data.get("sys.channel_id") or ""),
                status="running",
                current_run_id=run_id,
                variables={},
            )
        self._append_event(
            session_id=session_id,
            chatflow_id=chatflow_id,
            run_id=run_id,
            event_type="workflow_run_started",
            payload={
                "runId": run_id,
                "ownerType": self._owner_type,
                _owner_id_payload_key(self._owner_type): chatflow_id,
                "input": input_data,
                "idempotencyKey": idempotency_key or "",
                **_definition_payload(definition),
            },
        )
        payload = _start_payload(
            RuntimeV2Start(
                run_id=run_id,
                owner_type=self._owner_type,
                owner_id=chatflow_id,
                chatflow_id=chatflow_id,
                session_id=session_id,
                status="RUNNING",
                event_stream_ref=f"/api/v1/runtime-runs/{run_id}/events/stream?afterSequence=0",
                events_ref=f"/api/v1/runtime-runs/{run_id}/events",
                result_ref=f"/api/v1/runtime-runs/{run_id}/result",
                version_id=definition.get("versionId"),
                version=definition.get("version"),
            )
        )
        payload["idempotentReplay"] = False
        return payload

    def complete_run(self, run_id: int) -> None:
        run = self._run_or_404(run_id)
        if str(run["status"]) != "RUNNING":
            return
        time.sleep(self._completion_delay_seconds)
        run = self._run_or_404(run_id)
        if str(run["status"]) != "RUNNING":
            return
        chatflow_id = int(run["workflow_id"])
        session_id = self._session_id_for_run(chatflow_id, run_id)
        input_data = _runtime_user_input(dict(run.get("input") or {}))
        definition = _runtime_definition(dict(run.get("input") or {}))
        edges = definition.get("edges") if definition else self._repository.list_edges(chatflow_id)
        nodes = definition.get("nodes") if definition else self._repository.list_nodes(chatflow_id)
        context = _context_from_input(input_data)
        try:
            output = self._run_from_node(
                chatflow_id=chatflow_id,
                run_id=run_id,
                session_id=session_id,
                node_key=_next_node_key(edges, "start"),
                context=context,
                input_data=input_data,
                nodes=nodes,
                edges=edges,
            )
        except _RuntimeV2Interrupt as interrupted:
            if not self._run_has_status(run_id, "RUNNING"):
                return
            self._repository.finish_run(run_id, "INTERRUPTED", output=interrupted.output)
            if self._use_chatflow_session:
                self._state_repository.update_session_status(
                    chatflow_id=chatflow_id,
                    session_id=session_id,
                    status="waiting",
                    current_run_id=run_id,
                    variables=interrupted.variable_scopes,
                )
            self._append_event(
                session_id=session_id,
                chatflow_id=chatflow_id,
                run_id=run_id,
                event_type="workflow_run_interrupted",
                node_key=interrupted.node_key,
                payload={"output": interrupted.output},
            )
            return
        except Exception as exc:
            if not self._run_has_status(run_id, "RUNNING"):
                return
            self._repository.finish_run(run_id, "FAILED", output={}, error=str(exc))
            self._append_event(
                session_id=session_id,
                chatflow_id=chatflow_id,
                run_id=run_id,
                event_type="workflow_run_failed",
                payload={"error": str(exc)},
            )
            return
        if not self._run_has_status(run_id, "RUNNING"):
            return
        self._repository.finish_run(run_id, "SUCCEEDED", output=output)
        if self._use_chatflow_session:
            self._state_repository.update_session_status(
                chatflow_id=chatflow_id,
                session_id=session_id,
                status="completed",
                current_run_id=run_id,
                variables=context.scopes_snapshot(),
            )
        self._append_event(
            session_id=session_id,
            chatflow_id=chatflow_id,
            run_id=run_id,
            event_type="workflow_run_completed",
            payload={"output": output},
        )

    def resume_run(
        self,
        run_id: int,
        resume_data: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        run = self._run_or_404(run_id)
        chatflow_id = int(run["workflow_id"])
        if idempotency_key and self._state_repository.find_resume_event_by_idempotency_key(
            chatflow_id,
            run_id,
            idempotency_key,
        ):
            return self.get_result(run_id)
        checkpoint = self._state_repository.get_waiting_checkpoint(chatflow_id, run_id)
        if checkpoint is None:
            raise BizError(ErrorCode.NOT_FOUND, "Runtime v2 checkpoint not found")
        session_id = str(checkpoint["session_id"])
        pending_node_key = str(checkpoint["pending_node_key"])
        context = ExecutionContext()
        variable_scopes = checkpoint.get("variable_scopes")
        if isinstance(variable_scopes, dict):
            context.load_scopes(variable_scopes)
        node_outputs = checkpoint.get("node_outputs")
        if isinstance(node_outputs, dict):
            for node_key, output in node_outputs.items():
                if isinstance(output, dict):
                    context.set_output(str(node_key), output)
        runtime_definition = _runtime_definition(dict(run.get("input") or {}))
        input_data = dict((checkpoint.get("execution_context") or {}).get("input") or {})
        input_data["resume"] = {pending_node_key: resume_data}
        context.set_output("start", input_data)
        self._append_event(
            session_id=session_id,
            chatflow_id=chatflow_id,
            run_id=run_id,
            event_type="workflow_run_resumed",
            node_key=pending_node_key,
            payload={"resumeData": resume_data, "idempotencyKey": idempotency_key},
            checkpoint_id=int(checkpoint["id"]),
        )
        try:
            output = self._run_from_node(
                chatflow_id=chatflow_id,
                run_id=run_id,
                session_id=session_id,
                node_key=pending_node_key,
                context=context,
                input_data=input_data,
                nodes=runtime_definition.get("nodes") if runtime_definition else None,
                edges=runtime_definition.get("edges") if runtime_definition else None,
            )
        except _RuntimeV2Interrupt as interrupted:
            self._state_repository.mark_checkpoint_completed(int(checkpoint["id"]))
            self._repository.finish_run(run_id, "INTERRUPTED", output=interrupted.output)
            self._state_repository.update_session_status(
                chatflow_id=chatflow_id,
                session_id=session_id,
                status="waiting",
                current_run_id=run_id,
                variables=interrupted.variable_scopes,
            )
            self._append_event(
                session_id=session_id,
                chatflow_id=chatflow_id,
                run_id=run_id,
                event_type="workflow_run_interrupted",
                node_key=interrupted.node_key,
                payload={"output": interrupted.output},
            )
            return self.get_result(run_id)
        self._state_repository.mark_checkpoint_completed(int(checkpoint["id"]))
        self._repository.finish_run(run_id, "SUCCEEDED", output=output)
        self._state_repository.update_session_status(
            chatflow_id=chatflow_id,
            session_id=session_id,
            status="completed",
            current_run_id=run_id,
            variables=context.scopes_snapshot(),
        )
        self._append_event(
            session_id=session_id,
            chatflow_id=chatflow_id,
            run_id=run_id,
            event_type="workflow_run_completed",
            payload={"output": output},
        )
        return self.get_result(run_id)

    def cancel_run(self, run_id: int) -> dict[str, Any]:
        run = self._run_or_404(run_id)
        chatflow_id = int(run["workflow_id"])
        session_id = self._session_id_for_run(chatflow_id, run_id)
        owner_type = self._owner_type_for_run(run)
        run_status = str(run["status"]).upper()
        if run_status == "CANCELLED":
            result = self.get_result(run_id)
            result["cancellation"] = {
                "applied": False,
                "idempotent": True,
                "previousStatus": "CANCELLED",
                "reason": "Runtime v2 run was already cancelled.",
            }
            return result
        if run_status in _RUNTIME_V2_TERMINAL_STATUSES:
            result = self.get_result(run_id)
            result["cancellation"] = {
                "applied": False,
                "idempotent": False,
                "previousStatus": run_status,
                "reason": "Runtime v2 run is already terminal.",
            }
            return result
        if run_status not in _RUNTIME_V2_CANCELLABLE_STATUSES:
            raise BizError(ErrorCode.BAD_REQUEST, f"Runtime v2 run cannot be cancelled from status {run_status}")
        checkpoint = self._state_repository.get_waiting_checkpoint(chatflow_id, run_id)
        checkpoint_id = int(checkpoint["id"]) if checkpoint is not None else None
        if checkpoint_id is not None:
            self._state_repository.mark_checkpoint_completed(checkpoint_id)
        self._repository.finish_run(run_id, "CANCELLED", output={}, error="cancelled by operator")
        if self._use_chatflow_session and owner_type == "CHATFLOW":
            self._state_repository.update_session_status(
                chatflow_id=chatflow_id,
                session_id=session_id,
                status="cancelled",
                current_run_id=run_id,
            )
        self._append_event(
            session_id=session_id,
            chatflow_id=chatflow_id,
            run_id=run_id,
            event_type="workflow_run_cancelled",
            payload={
                "runId": run_id,
                "ownerType": owner_type,
                "previousStatus": run_status,
                "status": "CANCELLED",
                "checkpointId": checkpoint_id,
                "cancellation": {"applied": True, "idempotent": False},
            },
            checkpoint_id=checkpoint_id,
        )
        result = self.get_result(run_id)
        result["cancellation"] = {
            "applied": True,
            "idempotent": False,
            "previousStatus": run_status,
            "reason": "Runtime v2 run cancelled before further scheduling.",
        }
        return result

    def get_result(self, run_id: int) -> dict[str, Any]:
        run = self._run_or_404(run_id)
        chatflow_id = int(run["workflow_id"])
        owner_type = self._owner_type_for_run(run)
        runtime_metadata = _runtime_metadata(dict(run.get("input") or {}))
        checkpoint = self._state_repository.get_waiting_checkpoint(chatflow_id, run_id)
        result = {
            "runId": run_id,
            "ownerType": owner_type,
            "ownerId": chatflow_id,
            "status": str(run["status"]),
            "output": dict(run.get("output") or {}),
            "error": str(run.get("error") or ""),
            "checkpoint": _format_runtime_checkpoint(checkpoint),
            "eventsRef": f"/api/v1/runtime-runs/{run_id}/events",
            "eventStreamRef": f"/api/v1/runtime-runs/{run_id}/events/stream?afterSequence=0",
            "resultRef": f"/api/v1/runtime-runs/{run_id}/result",
        }
        result[_owner_id_payload_key(owner_type)] = chatflow_id
        if runtime_metadata.get("versionId") is not None:
            result["versionId"] = runtime_metadata.get("versionId")
            result["version"] = runtime_metadata.get("version")
        return result

    def list_events(self, run_id: int, after_sequence: int = 0) -> dict[str, Any]:
        run = self._run_or_404(run_id)
        events = [
            _format_runtime_event(event)
            for event in self._state_repository.list_events(int(run["workflow_id"]), run_id)
            if int(event["sequence"]) > after_sequence
        ]
        return {"list": events, "total": len(events)}

    def list_nodes(self, run_id: int) -> dict[str, Any]:
        self._run_or_404(run_id)
        rows = [_format_runtime_node_run(row, run_id) for row in self._repository.list_node_runs(run_id)]
        return {"list": rows, "total": len(rows)}

    def _run_from_node(
        self,
        *,
        chatflow_id: int,
        run_id: int,
        session_id: str,
        node_key: str | None,
        context: ExecutionContext,
        input_data: dict[str, Any],
        nodes: list[dict[str, Any]] | None = None,
        edges: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        node_rows = nodes if nodes is not None else self._repository.list_nodes(chatflow_id)
        edge_rows = edges if edges is not None else self._repository.list_edges(chatflow_id)
        nodes_by_key = {str(node["node_key"]): node for node in node_rows}
        current = node_key
        output: dict[str, Any] = {}
        while current:
            node = nodes_by_key.get(current)
            if node is None:
                raise ValueError(f"Unsupported runtime v2 node: {current}")
            node_output = self._execute_node(chatflow_id, run_id, session_id, node, context, input_data)
            context.set_output(current, node_output)
            output = node_output
            current = _next_node_key(edge_rows, current, node_output, str(node["type"]).upper())
        return output

    def _execute_node(
        self,
        chatflow_id: int,
        run_id: int,
        session_id: str,
        node: dict[str, Any],
        context: ExecutionContext,
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        node_key = str(node["node_key"])
        node_type = str(node["type"]).upper()
        started_at = time.perf_counter()
        node_run_id = self._repository.create_node_run(run_id, node_key, node_type, inputs=input_data)
        self._append_event(
            session_id=session_id,
            chatflow_id=chatflow_id,
            run_id=run_id,
            event_type="workflow_node_started",
            node_key=node_key,
            payload={"nodeType": node_type, "nodeRunId": node_run_id},
        )
        self._append_event(
            session_id=session_id,
            chatflow_id=chatflow_id,
            run_id=run_id,
            event_type="node_status_changed",
            node_key=node_key,
            payload={"nodeType": node_type, "nodeRunId": node_run_id, "status": "RUNNING"},
        )
        try:
            if node_type == "MESSAGE":
                config = dict(node.get("config") or {})
                if config.get("raiseError"):
                    raise ValueError(str(config.get("raiseError")))
                content = context.render(str(config.get("content") or ""))
                output = {str(config.get("outputVariable") or "content"): content}
            elif node_type == "QUESTION":
                output = self._question_output(chatflow_id, run_id, session_id, node, context, input_data)
            elif node_type == "HUMAN_INPUT":
                output = HumanInputNodeExecutor().execute(node, context)
            elif node_type == "CODE":
                output = CodeNodeExecutor().execute(node, context)
            elif node_type == "TEXT_PROCESS":
                output = TextProcessNodeExecutor().execute(node, context)
            elif node_type == "JSON_PARSE":
                output = JsonParseNodeExecutor().execute(node, context)
            elif node_type == "VARIABLE_AGGREGATION":
                output = VariableAggregationNodeExecutor().execute(node, context)
            elif node_type == "VARIABLE_ASSIGN":
                output = VariableAssignNodeExecutor().execute(node, context)
            elif node_type == "CONDITION":
                output = ConditionNodeExecutor().execute(node, context)
            elif node_type == "INTENT_RECOGNITION":
                output = IntentRecognitionNodeExecutor().execute(node, context)
            elif node_type == "INFORMATION_COLLECTION":
                output = InformationCollectionNodeExecutor().execute(node, context)
            elif node_type == "LLM":
                output = LlmNodeExecutor(
                    self._llm_completer_for(chatflow_id),
                    self._knowledge_facade,
                    self._mcp_tool_executor,
                ).execute(node, context)
            elif node_type == "KNOWLEDGE":
                if self._knowledge_facade is None:
                    raise ValueError("Runtime v2 KNOWLEDGE node requires KnowledgeFacade")
                output = KnowledgeNodeExecutor(self._knowledge_facade).execute(node, context)
            elif node_type == "API_CALL":
                reason = _runtime_v2_api_call_unsupported_reason(dict(node.get("config") or {}))
                if reason:
                    raise ValueError(f"Runtime v2 API_CALL is not compatible: {reason}")
                output = ApiCallNodeExecutor(self._api_tool_executor).execute(node, context)
                output = _with_runtime_v2_execution_evidence_defaults(output)
            elif node_type == "TOOL_CALL":
                reason = _runtime_v2_tool_call_unsupported_reason(dict(node.get("config") or {}))
                if reason:
                    raise ValueError(f"Runtime v2 TOOL_CALL is not compatible: {reason}")
                output = ToolCallNodeExecutor(self._mcp_tool_executor, self._api_tool_executor).execute(node, context)
                output = _with_runtime_v2_execution_evidence_defaults(output)
            elif node_type == "EXECUTE_WORKFLOW":
                output = self._execute_workflow_output(chatflow_id, node, context)
            elif node_type == "TRANSFER_TO_HUMAN":
                output = self._transfer_to_human_output(chatflow_id, run_id, session_id, node, context, input_data)
            elif node_type == "AGENT_CALL":
                output = AgentCallNodeExecutor(self._agent_invoker_for(chatflow_id)).execute(node, context)
            elif node_type == "END":
                output = EndNodeExecutor().execute(node, context)
            else:
                raise ValueError(f"Runtime v2 core coverage does not support node type: {node_type}")
        except _RuntimeV2Interrupt:
            self._repository.finish_node_run(node_run_id, "WAITING", {})
            self._append_event(
                session_id=session_id,
                chatflow_id=chatflow_id,
                run_id=run_id,
                event_type="node_status_changed",
                node_key=node_key,
                payload={"nodeType": node_type, "nodeRunId": node_run_id, "status": "WAITING"},
            )
            raise
        except WorkflowInterrupt as interrupted:
            self._checkpoint_workflow_interrupt(
                chatflow_id=chatflow_id,
                run_id=run_id,
                session_id=session_id,
                node_key=node_key,
                output=interrupted.output,
                context=context,
                input_data=input_data,
            )
            self._repository.finish_node_run(node_run_id, "WAITING", {})
            self._append_event(
                session_id=session_id,
                chatflow_id=chatflow_id,
                run_id=run_id,
                event_type="node_status_changed",
                node_key=node_key,
                payload={"nodeType": node_type, "nodeRunId": node_run_id, "status": "WAITING"},
            )
            raise _RuntimeV2Interrupt(
                node_key=node_key,
                output=interrupted.output,
                variable_scopes=context.scopes_snapshot(),
            ) from interrupted
        except Exception as exc:
            handled_output = _runtime_v2_handled_error_output(node_type, node, exc, started_at)
            if handled_output is not None:
                self._repository.finish_node_run(node_run_id, "SUCCEEDED", handled_output)
                self._append_event(
                    session_id=session_id,
                    chatflow_id=chatflow_id,
                    run_id=run_id,
                    event_type="workflow_node_error_handled",
                    node_key=node_key,
                    payload={
                        "nodeType": node_type,
                        "nodeRunId": node_run_id,
                        "errorBehavior": handled_output["errorBehavior"],
                        "route": handled_output.get("route"),
                        "error": handled_output["error"],
                        "output": handled_output,
                    },
                )
                self._append_event(
                    session_id=session_id,
                    chatflow_id=chatflow_id,
                    run_id=run_id,
                    event_type="workflow_node_completed",
                    node_key=node_key,
                    payload={"nodeType": node_type, "nodeRunId": node_run_id, "output": handled_output},
                )
                self._append_event(
                    session_id=session_id,
                    chatflow_id=chatflow_id,
                    run_id=run_id,
                    event_type="node_status_changed",
                    node_key=node_key,
                    payload={"nodeType": node_type, "nodeRunId": node_run_id, "status": "COMPLETED"},
                )
                return handled_output
            self._repository.finish_node_run(node_run_id, "FAILED", {}, error=str(exc))
            self._append_event(
                session_id=session_id,
                chatflow_id=chatflow_id,
                run_id=run_id,
                event_type="workflow_node_failed",
                node_key=node_key,
                payload={"nodeType": node_type, "nodeRunId": node_run_id, "error": str(exc)},
            )
            self._append_event(
                session_id=session_id,
                chatflow_id=chatflow_id,
                run_id=run_id,
                event_type="node_status_changed",
                node_key=node_key,
                payload={"nodeType": node_type, "nodeRunId": node_run_id, "status": "FAILED"},
            )
            raise
        self._repository.finish_node_run(node_run_id, "SUCCEEDED", output)
        self._append_event(
            session_id=session_id,
            chatflow_id=chatflow_id,
            run_id=run_id,
            event_type="workflow_node_completed",
            node_key=node_key,
            payload={"nodeType": node_type, "nodeRunId": node_run_id, "output": output},
        )
        self._append_event(
            session_id=session_id,
            chatflow_id=chatflow_id,
            run_id=run_id,
            event_type="node_status_changed",
            node_key=node_key,
            payload={"nodeType": node_type, "nodeRunId": node_run_id, "status": "COMPLETED"},
        )
        return output

    def _question_output(
        self,
        chatflow_id: int,
        run_id: int,
        session_id: str,
        node: dict[str, Any],
        context: ExecutionContext,
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        node_key = str(node["node_key"])
        config = dict(node.get("config") or {})
        resume_data = dict(dict(input_data.get("resume") or {}).get(node_key) or {})
        output_variable = str(config.get("outputVariable") or "answer")
        if resume_data:
            return {output_variable: resume_data.get(output_variable) or resume_data.get("answer") or ""}
        interrupt_payload = {
            "nodeKey": node_key,
            "question": context.render(str(config.get("question") or "")),
            "answerType": str(config.get("answerType") or "text"),
            "options": config.get("options") if isinstance(config.get("options"), list) else [],
            "resumeBehavior": str(config.get("resumeBehavior") or "wait"),
            "timeoutSeconds": _optional_int(config.get("timeoutSeconds") or config.get("timeout_seconds")) or 0,
        }
        checkpoint = self._state_repository.create_checkpoint(
            session_id=session_id,
            chatflow_id=chatflow_id,
            run_id=run_id,
            pending_node_key=node_key,
            execution_context={"input": input_data},
            node_outputs=context.outputs_snapshot(),
            variable_scopes=context.scopes_snapshot(),
            resume_schema=interrupt_payload,
        )
        event = self._append_event(
            session_id=session_id,
            chatflow_id=chatflow_id,
            run_id=run_id,
            event_type="workflow_node_waiting",
            node_key=node_key,
            payload=interrupt_payload,
            checkpoint_id=int(checkpoint["id"]),
        )
        self._state_repository.link_checkpoint_event(int(checkpoint["id"]), int(event["id"]))
        raise _RuntimeV2Interrupt(
            node_key=node_key,
            output={"interrupt": interrupt_payload},
            variable_scopes=context.scopes_snapshot(),
        )

    def _execute_workflow_output(
        self,
        workflow_id: int,
        node: dict[str, Any],
        context: ExecutionContext,
    ) -> dict[str, Any]:
        repository: Any = self._repository
        if self._publish_repository is not None:
            repository = _PublishedSnapshotWorkflowRepository(self._repository, self._publish_repository)
        target_workflow_id = _target_workflow_id_from_config(dict(node.get("config") or {}))
        output = ExecuteWorkflowNodeExecutor(
            repository,
            workflow_id,
            (),
            knowledge_facade=self._knowledge_facade,
            llm_completer=self._llm_completer_for(workflow_id),
            mcp_tool_executor=self._mcp_tool_executor,
            api_tool_executor=self._api_tool_executor,
            agent_invoker=self._agent_invoker_for(workflow_id),
        ).execute(node, context)
        output.update(_nested_version_output(repository, target_workflow_id))
        return output

    def _transfer_to_human_output(
        self,
        chatflow_id: int,
        run_id: int,
        session_id: str,
        node: dict[str, Any],
        context: ExecutionContext,
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        if self._flow_type != "CHATFLOW":
            raise ValueError("TRANSFER_TO_HUMAN is Chatflow-only")
        node_key = str(node["node_key"])
        config = dict(node.get("config") or {})
        resume_data = dict(dict(input_data.get("resume") or {}).get(node_key) or {})
        queue = str(config.get("queue") or config.get("team") or "general")
        reason = str(config.get("reason") or config.get("category") or "user_request")
        priority = str(config.get("priority") or "normal")
        if resume_data:
            output = {
                "handoff_id": resume_data.get("handoff_id") or resume_data.get("handoffId") or "",
                "handoff_status": resume_data.get("handoff_status") or resume_data.get("status") or "resolved",
                "queue": resume_data.get("queue") or queue,
                "reason": resume_data.get("reason") or reason,
                "priority": resume_data.get("priority") or priority,
                "answer": resume_data.get("answer") or resume_data.get("message") or "",
                "resumed": True,
                "mocked": True,
            }
            for key, value in resume_data.items():
                output.setdefault(str(key), value)
            return output

        message = context.render(str(config.get("message") or "已为你转接人工客服，请稍候。"))
        handoff_id = f"runtime-v2-handoff-{run_id}-{node_key}"
        interrupt_payload = {
            "type": "TRANSFER_TO_HUMAN",
            "nodeKey": node_key,
            "handoffId": handoff_id,
            "queue": queue,
            "status": "waiting",
            "message": message,
            "reason": reason,
            "priority": priority,
            "mocked": True,
        }
        checkpoint = self._state_repository.create_checkpoint(
            session_id=session_id,
            chatflow_id=chatflow_id,
            run_id=run_id,
            pending_node_key=node_key,
            execution_context={"input": input_data},
            node_outputs=context.outputs_snapshot(),
            variable_scopes=context.scopes_snapshot(),
            resume_schema=interrupt_payload,
        )
        checkpoint_id = int(checkpoint["id"])
        waiting_event = self._append_event(
            session_id=session_id,
            chatflow_id=chatflow_id,
            run_id=run_id,
            event_type="workflow_node_waiting",
            node_key=node_key,
            payload=interrupt_payload,
            checkpoint_id=checkpoint_id,
        )
        self._append_event(
            session_id=session_id,
            chatflow_id=chatflow_id,
            run_id=run_id,
            event_type="handoff_requested",
            node_key=node_key,
            payload={
                "nodeType": "TRANSFER_TO_HUMAN",
                "handoffId": handoff_id,
                "queue": queue,
                "priority": priority,
                "reason": reason,
                "status": "waiting",
                "message": message,
                "mocked": True,
            },
            checkpoint_id=checkpoint_id,
        )
        self._state_repository.link_checkpoint_event(checkpoint_id, int(waiting_event["id"]))
        raise _RuntimeV2Interrupt(
            node_key=node_key,
            output={
                "handoff_id": handoff_id,
                "handoff_status": "waiting",
                "queue": queue,
                "assignee": "",
                "reason": reason,
                "priority": priority,
                "events": [
                    {"type": "message_done", "nodeKey": node_key, "content": message},
                    {
                        "type": "handoff_requested",
                        "nodeKey": node_key,
                        "handoffId": handoff_id,
                        "queue": queue,
                        "priority": priority,
                        "reason": reason,
                    },
                ],
                "interrupt": interrupt_payload,
                "mocked": True,
            },
            variable_scopes=context.scopes_snapshot(),
        )

    def _checkpoint_workflow_interrupt(
        self,
        *,
        chatflow_id: int,
        run_id: int,
        session_id: str,
        node_key: str,
        output: dict[str, Any],
        context: ExecutionContext,
        input_data: dict[str, Any],
    ) -> None:
        interrupt_payload = dict(output.get("interrupt") or {})
        if not interrupt_payload:
            interrupt_payload = {"nodeKey": node_key, "type": "INTERRUPT"}
        interrupt_payload.setdefault("nodeKey", node_key)
        checkpoint = self._state_repository.create_checkpoint(
            session_id=session_id,
            chatflow_id=chatflow_id,
            run_id=run_id,
            pending_node_key=node_key,
            execution_context={"input": input_data},
            node_outputs=context.outputs_snapshot(),
            variable_scopes=context.scopes_snapshot(),
            resume_schema=interrupt_payload,
        )
        event = self._append_event(
            session_id=session_id,
            chatflow_id=chatflow_id,
            run_id=run_id,
            event_type="workflow_node_waiting",
            node_key=node_key,
            payload=interrupt_payload,
            checkpoint_id=int(checkpoint["id"]),
        )
        self._state_repository.link_checkpoint_event(int(checkpoint["id"]), int(event["id"]))

    def _append_event(
        self,
        *,
        session_id: str,
        chatflow_id: int,
        run_id: int,
        event_type: str,
        node_key: str = "",
        payload: dict[str, Any] | None = None,
        checkpoint_id: int | None = None,
    ) -> dict[str, Any]:
        event_payload = {
            **_runtime_event_debug_metadata(dict(self._run_or_404(run_id).get("input") or {})),
            **(payload or {}),
        }
        return self._state_repository.append_event(
            session_id=session_id,
            chatflow_id=chatflow_id,
            run_id=run_id,
            event_type=event_type,
            node_key=node_key,
            payload=_runtime_event_payload(
                level="L1",
                source=f"{self._owner_type.lower()}_runtime_v2",
                actor="system",
                **event_payload,
            ),
            checkpoint_id=checkpoint_id,
        )

    def _run_or_404(self, run_id: int) -> dict[str, Any]:
        run = self._repository.get_run(run_id)
        if run is None:
            raise BizError(ErrorCode.NOT_FOUND, "Runtime v2 run not found")
        return run

    def _llm_completer_for(self, chatflow_id: int) -> WorkflowLlmCompleter | None:
        if self._llm_completer is not None:
            return self._llm_completer
        if self._llm_completer_resolver is None:
            return None
        if chatflow_id not in self._llm_completer_cache:
            self._llm_completer_cache[chatflow_id] = self._llm_completer_resolver(chatflow_id)
        return self._llm_completer_cache[chatflow_id]

    def _agent_invoker_for(self, chatflow_id: int) -> AgentInvocationFacade | None:
        if self._agent_invoker_resolver is None:
            return None
        if chatflow_id not in self._agent_invoker_cache:
            self._agent_invoker_cache[chatflow_id] = self._agent_invoker_resolver(chatflow_id)
        return self._agent_invoker_cache[chatflow_id]

    def _run_has_status(self, run_id: int, status: str) -> bool:
        run = self._run_or_404(run_id)
        return str(run["status"]).upper() == status.upper()

    def _ensure_owner(self, chatflow_id: int) -> None:
        if self._repository.get(chatflow_id, self._flow_type) is None:
            label = "Workflow" if self._flow_type == "WORKFLOW" else "Chatflow"
            raise BizError(ErrorCode.NOT_FOUND, f"{label} not found")

    def _definition_for_start(self, chatflow_id: int, version_id: int | None = None) -> dict[str, Any]:
        published = self._published_version_for_start(chatflow_id, version_id)
        if published is not None:
            return _definition_from_published_version(published)
        if self._owner_type == "WORKFLOW":
            if self._publish_repository is None:
                raise BizError(ErrorCode.BAD_REQUEST, "Workflow v2 requires publish repository")
            raise BizError(ErrorCode.BAD_REQUEST, "Workflow v2 requires an active published version")
        if version_id is not None:
            raise BizError(ErrorCode.NOT_FOUND, "Published version not found")
        return {
            "nodes": self._repository.list_nodes(chatflow_id),
            "edges": self._repository.list_edges(chatflow_id),
            "definitionSource": "draft",
        }

    def _published_version_for_start(self, chatflow_id: int, version_id: int | None) -> dict[str, Any] | None:
        if self._publish_repository is None:
            return None
        if version_id is None:
            return self._publish_repository.active_version(chatflow_id, self._flow_type)
        row = self._publish_repository.get_version(chatflow_id, self._flow_type, version_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Published version not found")
        return row

    def _owner_type_for_run(self, run: dict[str, Any]) -> str:
        metadata = _runtime_metadata(dict(run.get("input") or {}))
        owner_type = str(metadata.get("ownerType") or "").upper()
        if owner_type in {"WORKFLOW", "CHATFLOW"}:
            return owner_type
        workflow = self._repository.get(int(run["workflow_id"]))
        flow_type = str((workflow or {}).get("flow_type") or self._owner_type).upper()
        return "WORKFLOW" if flow_type == "WORKFLOW" else "CHATFLOW"

    def _session_id_for_run(self, chatflow_id: int, run_id: int) -> str:
        events = self._state_repository.list_events(chatflow_id, run_id)
        if events:
            return str(events[0]["session_id"])
        return f"chatflow-v2-{run_id}"


class WorkflowRuntimeV2Service(ChatflowRuntimeV2Service):
    def __init__(
        self,
        repository: WorkflowRepository,
        state_repository: ChatflowStateRepository,
        publish_repository: WorkflowPublishRepository,
        *,
        completion_delay_seconds: float = 0.45,
        knowledge_facade: KnowledgeFacade | None = None,
        llm_completer: WorkflowLlmCompleter | None = None,
        llm_completer_resolver: RuntimeV2LlmCompleterResolver | None = None,
        agent_invoker_resolver: RuntimeV2AgentInvokerResolver | None = None,
        mcp_tool_executor: McpToolExecutor | None = None,
        api_tool_executor: ApiToolExecutor | None = None,
    ) -> None:
        super().__init__(
            repository,
            state_repository,
            completion_delay_seconds=completion_delay_seconds,
            owner_type="WORKFLOW",
            flow_type="WORKFLOW",
            use_chatflow_session=False,
            publish_repository=publish_repository,
            knowledge_facade=knowledge_facade,
            llm_completer=llm_completer,
            llm_completer_resolver=llm_completer_resolver,
            agent_invoker_resolver=agent_invoker_resolver,
            mcp_tool_executor=mcp_tool_executor,
            api_tool_executor=api_tool_executor,
        )


class _PublishedSnapshotWorkflowRepository:
    def __init__(self, base: WorkflowRepository, publish_repository: WorkflowPublishRepository) -> None:
        self._base = base
        self._publish_repository = publish_repository
        self._version_cache: dict[int, Mapping[str, Any] | None] = {}

    def active_version_for(self, workflow_id: int) -> Mapping[str, Any] | None:
        if workflow_id not in self._version_cache:
            self._version_cache[workflow_id] = self._publish_repository.active_version(workflow_id, "WORKFLOW")
        return self._version_cache[workflow_id]

    def list_nodes(self, workflow_id: int) -> list[dict[str, Any]]:
        snapshot = self._snapshot_for(workflow_id)
        if snapshot is None:
            return self._base.list_nodes(workflow_id)
        nodes = snapshot.get("nodes")
        return [dict(node) for node in nodes] if isinstance(nodes, list) else []

    def list_edges(self, workflow_id: int) -> list[dict[str, Any]]:
        snapshot = self._snapshot_for(workflow_id)
        if snapshot is None:
            return self._base.list_edges(workflow_id)
        edges = snapshot.get("edges")
        return [dict(edge) for edge in edges] if isinstance(edges, list) else []

    def get(self, workflow_id: int, flow_type: str | None = None) -> dict[str, Any] | None:
        return self._base.get(workflow_id, flow_type)

    def create_run(self, workflow_id: int, input_values: dict[str, Any]) -> int:
        version = self.active_version_for(workflow_id)
        if version is not None:
            input_values = _with_nested_version_metadata(input_values, version)
        return self._base.create_run(workflow_id, input_values)

    def finish_run(
        self,
        run_id: int,
        status: str,
        output: dict[str, Any],
        error: str = "",
        elapsed_ms: int = 0,
    ) -> None:
        self._base.finish_run(run_id, status, output, error, elapsed_ms)

    def create_node_run(
        self,
        workflow_run_id: int,
        node_key: str,
        node_type: str,
        inputs: dict[str, Any] | None = None,
    ) -> int:
        return self._base.create_node_run(workflow_run_id, node_key, node_type, inputs=inputs)

    def finish_node_run(
        self,
        node_run_id: int,
        status: str,
        outputs: dict[str, Any],
        error: str = "",
        elapsed_ms: int = 0,
    ) -> None:
        self._base.finish_node_run(node_run_id, status, outputs, error, elapsed_ms)

    def list_node_runs(self, run_id: int) -> list[dict[str, Any]]:
        return self._base.list_node_runs(run_id)

    def _snapshot_for(self, workflow_id: int) -> Mapping[str, Any] | None:
        version = self.active_version_for(workflow_id)
        if version is None:
            return None
        snapshot = version.get("snapshot")
        return snapshot if isinstance(snapshot, Mapping) else None


class _RuntimeV2Interrupt(Exception):
    def __init__(self, *, node_key: str, output: dict[str, Any], variable_scopes: dict[str, Any]) -> None:
        super().__init__("Runtime v2 interrupted")
        self.node_key = node_key
        self.output = output
        self.variable_scopes = variable_scopes


def _start_payload(start: RuntimeV2Start) -> dict[str, Any]:
    refs = RuntimeV2RefBuilder.build(owner_type=start.owner_type, owner_id=start.owner_id, run_id=start.run_id)
    payload = {
        "runId": start.run_id,
        "ownerType": start.owner_type,
        "ownerId": start.owner_id,
        "sessionId": start.session_id,
        "status": start.status,
        "eventStreamRef": refs["eventStreamRef"],
        "eventsRef": refs["eventsRef"],
        "nodesRef": refs["nodesRef"],
        "resultRef": refs["resultRef"],
        "transport": {
            "decision": "sse",
            "webSocket": "deferred_until_bidirectional_control",
            "redisPubsub": "deferred_until_multi_process_fanout",
        },
    }
    payload[_owner_id_payload_key(start.owner_type)] = start.owner_id
    if start.version_id is not None:
        payload["versionId"] = start.version_id
        payload["version"] = start.version
    if start.owner_type == "WORKFLOW":
        payload["debugUrl"] = f"/workflows/{start.owner_id}/canvas?runId={start.run_id}&debug=1&runtime=v2"
    return payload


def _nested_version_output(repository: Any, target_workflow_id: int | None) -> dict[str, int]:
    if target_workflow_id is None or not isinstance(repository, _PublishedSnapshotWorkflowRepository):
        return {}
    version = repository.active_version_for(target_workflow_id)
    if version is None:
        return {}
    return {"nestedVersionId": int(version["id"]), "nestedVersion": int(version["version"])}


def _with_nested_version_metadata(input_values: dict[str, Any], version: Mapping[str, Any]) -> dict[str, Any]:
    runtime_metadata = input_values.get("_runtimeV2")
    metadata = dict(runtime_metadata) if isinstance(runtime_metadata, Mapping) else {}
    metadata["definitionSource"] = "published"
    metadata["versionId"] = int(version["id"])
    metadata["version"] = int(version["version"])
    return {**dict(input_values), "_runtimeV2": metadata}


def _target_workflow_id_from_config(config: Mapping[str, Any]) -> int | None:
    raw_id = config.get("targetWorkflowId") or config.get("target_workflow_id") or config.get("workflowId")
    if raw_id in (None, ""):
        return None
    try:
        return int(raw_id)
    except (TypeError, ValueError):
        return None


def _context_from_input(input_data: dict[str, Any]) -> ExecutionContext:
    context = ExecutionContext()
    context.set_output("start", input_data)
    for key, value in input_data.items():
        if "." not in str(key):
            continue
        scope, variable_name = str(key).split(".", 1)
        try:
            context.set_scope_value(scope, variable_name, value)
        except ValueError:
            continue
    return context


def _definition_from_published_version(published: dict[str, Any]) -> dict[str, Any]:
    snapshot = published.get("snapshot") if isinstance(published.get("snapshot"), dict) else {}
    nodes = snapshot.get("nodes") if isinstance(snapshot.get("nodes"), list) else []
    edges = snapshot.get("edges") if isinstance(snapshot.get("edges"), list) else []
    return {
        "nodes": [dict(node) for node in nodes if isinstance(node, dict)],
        "edges": [dict(edge) for edge in edges if isinstance(edge, dict)],
        "versionId": int(published["id"]),
        "version": int(published["version"]),
        "definitionSource": "published",
    }


def _with_runtime_metadata(
    input_data: dict[str, Any],
    owner_type: str,
    definition: dict[str, Any],
) -> dict[str, Any]:
    metadata = {
        "ownerType": owner_type,
        "definition": {
            "nodes": _json_safe(definition.get("nodes") or []),
            "edges": _json_safe(definition.get("edges") or []),
        },
        "definitionSource": definition.get("definitionSource") or "",
    }
    if definition.get("versionId") is not None:
        metadata["versionId"] = definition.get("versionId")
        metadata["version"] = definition.get("version")
    return {**dict(input_data), "_runtimeV2": metadata}


def _runtime_metadata(input_data: dict[str, Any]) -> dict[str, Any]:
    metadata = input_data.get("_runtimeV2")
    return dict(metadata) if isinstance(metadata, dict) else {}


def _runtime_event_debug_metadata(input_data: dict[str, Any]) -> dict[str, Any]:
    metadata = _runtime_metadata(input_data)
    event_metadata: dict[str, Any] = {}
    caller_context = input_data.get("callerContext") or input_data.get("caller_context")
    if isinstance(caller_context, dict):
        event_metadata["callerContext"] = dict(caller_context)
    if metadata.get("definitionSource"):
        event_metadata["definitionSource"] = metadata.get("definitionSource")
    if metadata.get("versionId") is not None:
        event_metadata["versionId"] = metadata.get("versionId")
        event_metadata["version"] = metadata.get("version")
    return event_metadata


def _runtime_definition(input_data: dict[str, Any]) -> dict[str, Any]:
    metadata = _runtime_metadata(input_data)
    definition = metadata.get("definition")
    if not isinstance(definition, dict):
        return {}
    nodes = definition.get("nodes") if isinstance(definition.get("nodes"), list) else []
    edges = definition.get("edges") if isinstance(definition.get("edges"), list) else []
    return {
        "nodes": [dict(node) for node in nodes if isinstance(node, dict)],
        "edges": [dict(edge) for edge in edges if isinstance(edge, dict)],
    }


def _runtime_user_input(input_data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in input_data.items() if key != "_runtimeV2"}


def _definition_payload(definition: dict[str, Any]) -> dict[str, Any]:
    payload = {"definitionSource": str(definition.get("definitionSource") or "")}
    if definition.get("versionId") is not None:
        payload["versionId"] = definition.get("versionId")
        payload["version"] = definition.get("version")
    return payload


def _owner_id_payload_key(owner_type: str) -> str:
    return "workflowId" if owner_type.upper() == "WORKFLOW" else "chatflowId"


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _next_node_key(
    edges: list[dict[str, Any]],
    source: str,
    output: dict[str, Any] | None = None,
    node_type: str = "",
) -> str | None:
    if node_type in {"CONDITION", "INTENT_RECOGNITION"}:
        branch_value = str(next(iter((output or {}).values()), ""))
        picked = ConditionBranchPicker().pick(source, edges, branch_value)
        if picked is not None:
            return picked
    branch_value = (output or {}).get("route") or (output or {}).get("branch")
    if branch_value is not None:
        picked = ConditionBranchPicker().pick(source, edges, str(branch_value))
        if picked is not None:
            return picked
    for edge in edges:
        if str(edge["source_node_key"]) == source and not edge.get("condition_expr"):
            return str(edge["target_node_key"])
    return None


def _requires_llm_information_collection(config: dict[str, Any]) -> bool:
    extractor_mode = str(config.get("extractorMode") or config.get("extractor_mode") or "fake").lower()
    return extractor_mode in {"llm", "model", "ai"}


def _runtime_v2_api_call_unsupported_reason(config: dict[str, Any]) -> str:
    resource_id = str(config.get("resourceId") or config.get("resource_id") or "").strip()
    if not resource_id:
        return "api_call_requires_api_resource"
    if not (resource_id.startswith("api-resource:") or resource_id.isdigit()):
        return "api_call_requires_api_resource"
    return ""


def _runtime_v2_tool_call_unsupported_reason(config: dict[str, Any]) -> str:
    resource_type = str(config.get("resourceType") or config.get("resource_type") or config.get("type") or "MCP_TOOL")
    resource_type = resource_type.strip().upper().replace("-", "_")
    resource_id = str(config.get("resourceId") or config.get("resource_id") or "").strip()
    tool_name = str(config.get("toolName") or config.get("tool_name") or config.get("name") or "").strip()
    if not resource_id or not tool_name:
        return "tool_call_requires_resource"
    if resource_type in {"API_TOOL", "API_RESOURCE"}:
        if resource_type in {"API_TOOL", "API_RESOURCE"} and not (
            resource_id.startswith("api-tool:") or resource_id.startswith("api-resource:") or resource_id.isdigit()
        ):
            return "tool_call_requires_resource"
    if resource_type == "MCP_TOOL" and not _runtime_v2_has_server_ids(config):
        return "tool_call_requires_resource"
    return ""


def _runtime_v2_allows_error_branching(node_type: str, config: dict[str, Any]) -> bool:
    return node_type in _RUNTIME_V2_ERROR_POLICY_NODE_TYPES and _runtime_v2_error_behavior(config) == "branch"


def _runtime_v2_has_server_ids(config: dict[str, Any]) -> bool:
    server_ids = config.get("serverIds") if "serverIds" in config else config.get("server_ids")
    if isinstance(server_ids, list):
        return any(_optional_int(item) is not None for item in server_ids)
    raw_server_id = config.get("serverId") if "serverId" in config else config.get("server_id")
    return _optional_int(raw_server_id) is not None


def _runtime_v2_error_behavior(config: dict[str, Any]) -> str:
    return str(config.get("errorBehavior") or config.get("error_behavior") or "fail").strip().lower() or "fail"


def _runtime_v2_handled_error_output(
    node_type: str,
    node: dict[str, Any],
    exc: Exception,
    started_at: float,
) -> dict[str, Any] | None:
    if node_type not in _RUNTIME_V2_ERROR_POLICY_NODE_TYPES:
        return None
    config = dict(node.get("config") or {})
    error_behavior = _runtime_v2_error_behavior(config)
    if error_behavior not in {"continue", "branch"}:
        return None
    error_message = str(exc)
    latency_ms = max(0, int((time.perf_counter() - started_at) * 1000))
    evidence = {
        "status": "FAILED",
        "errorMessage": error_message,
        "latencyMs": latency_ms,
        "retryCount": 0,
        "attempts": 1,
        "handled": True,
        "errorBehavior": error_behavior,
    }
    output: dict[str, Any] = {
        "success": False,
        "error": error_message,
        "errorBehavior": error_behavior,
        "evidence": evidence,
    }
    if error_behavior == "branch":
        output["route"] = "error"
        evidence["route"] = "error"
    output_variable = str(config.get("outputVariable") or config.get("output_variable") or "").strip()
    if output_variable and output_variable not in output:
        output[output_variable] = ""
    return output


def _with_runtime_v2_execution_evidence_defaults(output: dict[str, Any]) -> dict[str, Any]:
    evidence = output.get("evidence")
    if not isinstance(evidence, dict):
        return output
    enriched = dict(evidence)
    enriched.setdefault("status", "FAILED" if enriched.get("errorMessage") else "SUCCEEDED")
    enriched.setdefault("errorMessage", "")
    enriched.setdefault("latencyMs", 0)
    enriched.setdefault("retryCount", 0)
    enriched.setdefault("attempts", 1)
    return {**output, "evidence": enriched}


def _format_runtime_event(event: dict[str, Any]) -> dict[str, Any]:
    payload = dict(event.get("payload") or {})
    formatted = {
        "id": int(event["id"]),
        "runId": int(event["run_id"]),
        "sequence": int(event["sequence"]),
        "type": str(event["event_type"]),
        "level": str(payload.get("level") or "L1"),
        "source": str(payload.get("source") or "runtime_v2"),
        "actor": str(payload.get("actor") or "system"),
        "nodeId": str(event.get("node_key") or ""),
        "checkpointId": int(event["checkpoint_id"]) if event.get("checkpoint_id") else None,
        "spanId": payload.get("spanId"),
        "parentSpanId": payload.get("parentSpanId"),
        "payload": payload,
        "createdAt": format_datetime(event["created_at"]),
    }
    formatted["observability"] = _runtime_event_observability(formatted)
    return formatted


def _runtime_event_observability(event: dict[str, Any]) -> dict[str, Any]:
    payload = dict(event.get("payload") or {})
    return {
        "sourceKind": _runtime_source_kind(str(event.get("source") or "")),
        "eventMode": "live",
        "nodeState": _runtime_event_node_state(str(event.get("type") or ""), payload),
        "correlationRefs": {
            "runtimeRunId": int(event["runId"]),
            "sourceEventId": int(event["id"]),
            "sourceSequence": int(event["sequence"]),
            "nodeRunId": _positive_int(payload.get("nodeRunId")),
            "nodeKey": str(event.get("nodeId") or ""),
        },
    }


def _runtime_source_kind(source: str) -> str:
    if source.startswith("chatflow_"):
        return "chatflow"
    if source.startswith("workflow_"):
        return "workflow"
    return "runtime"


def _runtime_event_node_state(event_type: str, payload: dict[str, Any]) -> str:
    status = str(payload.get("status") or "").upper()
    if status:
        return status
    return {
        "workflow_node_started": "RUNNING",
        "workflow_node_completed": "COMPLETED",
        "workflow_node_failed": "FAILED",
        "workflow_node_waiting": "WAITING",
        "workflow_node_skipped": "SKIPPED",
        "handoff_requested": "WAITING",
    }.get(event_type, "")


def _positive_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _format_runtime_node_run(row: dict[str, Any], run_id: int) -> dict[str, Any]:
    formatted = {
        "id": int(row["id"]),
        "runId": run_id,
        "nodeKey": str(row["node_key"]),
        "nodeType": str(row["node_type"]),
        "status": _node_status(str(row["status"])),
        "inputs": dict(row.get("inputs") or {}),
        "outputs": dict(row.get("outputs") or {}),
        "error": str(row.get("error") or ""),
        "eventsRef": f"/api/v1/runtime-runs/{run_id}/events",
        "createdAt": format_datetime(row["created_at"]),
        "finishedAt": format_datetime(row["finished_at"]) if row.get("finished_at") else None,
    }
    formatted["observability"] = {
        "sourceKind": "runtime",
        "eventMode": "durable_replay",
        "nodeState": formatted["status"],
        "correlationRefs": {
            "runtimeRunId": run_id,
            "nodeRunId": formatted["id"],
            "nodeKey": formatted["nodeKey"],
        },
    }
    return formatted


def _node_status(status: str) -> str:
    return {
        "SUCCEEDED": "COMPLETED",
        "RUNNING": "RUNNING",
        "FAILED": "FAILED",
        "SKIPPED": "SKIPPED",
        "WAITING": "WAITING",
    }.get(status.upper(), status.upper())


def _runtime_event_payload(**payload: Any) -> dict[str, Any]:
    input_payload = payload.get("input")
    caller_context = {}
    if isinstance(input_payload, dict):
        caller_context = dict(input_payload.get("callerContext") or input_payload.get("caller_context") or {})
    if not caller_context:
        direct_caller_context = payload.get("callerContext") or payload.get("caller_context")
        if isinstance(direct_caller_context, dict):
            caller_context = dict(direct_caller_context)
    return {
        "schemaVersion": "runtime.v2.event/1",
        **_redact_payload(payload),
        "callerContext": _redact_payload(caller_context),
    }


def _redact_payload(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).lower() in _SECRET_KEYS:
                redacted[str(key)] = "[REDACTED]"
            else:
                redacted[str(key)] = _redact_payload(item)
        return redacted
    if isinstance(value, list):
        return [_redact_payload(item) for item in value]
    return value


def _format_runtime_checkpoint(checkpoint: dict[str, Any] | None) -> dict[str, Any] | None:
    if checkpoint is None:
        return None
    return {
        "id": int(checkpoint["id"]),
        "eventId": int(checkpoint["event_id"]) if checkpoint.get("event_id") else None,
        "pendingNodeKey": str(checkpoint["pending_node_key"]),
        "resumeSchema": dict(checkpoint.get("resume_schema") or {}),
        "status": str(checkpoint["status"]),
        "expiresAt": format_datetime(checkpoint["expires_at"]) if checkpoint.get("expires_at") else None,
    }
