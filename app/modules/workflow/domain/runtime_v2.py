from __future__ import annotations

import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from app.core.errors import BizError, ErrorCode
from app.modules.knowledge.api.facade import KnowledgeFacade
from app.modules.runtime.domain.external_call_governance import (
    ExternalCallGovernance,
    ExternalCallGovernanceError,
    external_call_policy_from_config,
)
from app.modules.runtime.domain.scheduler import compute_frontier
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
from app.modules.workflow.infra.runtime_job_repository import RuntimeJobRepository
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
_RUNTIME_V2_EXTERNAL_CALL_NODE_TYPES = {"LLM", "API_CALL", "TOOL_CALL", "KNOWLEDGE"}
_RUNTIME_V2_PRESTART_WAVE_NODE_TYPES = {
    "LLM",
    "KNOWLEDGE",
    "AGENT_CALL",
    "API_CALL",
    "TOOL_CALL",
    "EXECUTE_WORKFLOW",
}
_RUNTIME_V2_PARALLEL_WAVE_NODE_TYPES = {
    "API_CALL",
}
_RUNTIME_V2_SIDE_EFFECT_PROTECTION: dict[str, tuple[str, str]] = {
    "MESSAGE": ("message_send", "idempotency_key"),
    "VARIABLE_ASSIGN": ("runtime_variable_write", "execution_record"),
    "API_CALL": ("external_api_call", "idempotency_key"),
    "TOOL_CALL": ("tool_call", "idempotency_key"),
    "EXECUTE_WORKFLOW": ("nested_workflow_run", "idempotency_key"),
    "TRANSFER_TO_HUMAN": ("handoff_request", "proposed_action"),
}
RuntimeV2LlmCompleterResolver = Callable[[int], WorkflowLlmCompleter | None]
RuntimeV2AgentInvokerResolver = Callable[[int], AgentInvocationFacade | None]
_RUNTIME_EXTERNAL_CALL_GOVERNANCE = ExternalCallGovernance()


class _PreloadedApiResourceExecutor:
    def __init__(self, base_executor: ApiToolExecutor, rows_by_resource_id: dict[str, dict[str, Any]]) -> None:
        self._base_executor = base_executor
        self._rows_by_resource_id = rows_by_resource_id

    def execute_api_resource(
        self,
        resource_id: str,
        arguments: dict[str, object],
        overrides: dict[str, Any] | None = None,
        timeout_ms: int | None = None,
    ) -> Any:
        row = self._rows_by_resource_id.get(_api_resource_cache_key(resource_id))
        invoke_resource = getattr(self._base_executor, "_invoke_resource", None)
        if row is None or not callable(invoke_resource):
            return self._base_executor.execute_api_resource(resource_id, arguments, overrides, timeout_ms)
        return invoke_resource(row, arguments, overrides=overrides, timeout_ms=timeout_ms)

    def execute_api_tool(
        self,
        resource_id: str,
        tool_name: str,
        arguments: dict[str, object],
        timeout_ms: int | None = None,
    ) -> Any:
        return self._base_executor.execute_api_tool(resource_id, tool_name, arguments, timeout_ms)


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
                and not _runtime_v2_allows_default_fanout(source_config)
            ):
                if "branching_edges" not in unsupported_patterns:
                    unsupported_patterns.append("branching_edges")
        endpoint_issues = validate_node_endpoints(nodes, edges)
        contract_issues = validate_node_contracts(nodes)
        reference_issues = validate_variable_references(nodes)
        validation_issues = [*endpoint_issues, *contract_issues, *reference_issues]
        branch_validation_errors = [issue["code"] for issue in validation_issues]
        errors: list[dict[str, str]] = []
        for item in unsupported_nodes:
            _append_runtime_v2_error(errors, _runtime_v2_unsupported_node_error(item))
        for issue in endpoint_issues:
            category = (
                "branch_edges_incomplete"
                if issue["nodeType"] in {"CONDITION", "INTENT_RECOGNITION"}
                else "node_endpoints_incomplete"
            )
            _append_runtime_v2_error(errors, _runtime_v2_validation_error(issue, category))
        for issue in contract_issues:
            _append_runtime_v2_error(errors, _runtime_v2_validation_error(issue, "node_contract_invalid"))
        for issue in reference_issues:
            _append_runtime_v2_error(errors, _runtime_v2_validation_error(issue, "variable_references_invalid"))
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
            "errors": errors,
            "supportedNodeTypes": sorted(_SUPPORTED_CORE_NODE_TYPES),
        }


def _append_runtime_v2_error(errors: list[dict[str, str]], error: dict[str, str]) -> None:
    if not any(item.get("code") == error.get("code") for item in errors):
        errors.append(error)


def _runtime_v2_validation_error(issue: Mapping[str, str], category: str) -> dict[str, str]:
    return {
        "nodeKey": str(issue.get("nodeKey") or ""),
        "nodeType": str(issue.get("nodeType") or ""),
        "code": str(issue.get("code") or ""),
        "message": str(issue.get("message") or ""),
        "category": category,
        "reason": str(issue.get("reason") or category),
    }


def _runtime_v2_unsupported_node_error(item: Mapping[str, str]) -> dict[str, str]:
    node_key = str(item.get("nodeKey") or "")
    node_type = str(item.get("nodeType") or "")
    reason = str(item.get("reason") or "unsupported_node_type")
    if reason == "api_call_requires_api_resource":
        return {
            "nodeKey": node_key,
            "nodeType": node_type,
            "code": f"{node_key}.resourceId",
            "message": (
                f"{node_key} must use an API Resource reference like api-resource:<id>; "
                "raw URL mode is not supported by Runtime V2"
            ),
            "category": "node_contract_invalid",
            "reason": reason,
        }
    if reason == "tool_call_requires_resource":
        return {
            "nodeKey": node_key,
            "nodeType": node_type,
            "code": f"{node_key}.resourceId",
            "message": f"{node_key} must declare resourceId, toolName, and serverIds or API resource binding",
            "category": "node_contract_invalid",
            "reason": reason,
        }
    if reason == "llm_dependent_information_collection":
        return {
            "nodeKey": node_key,
            "nodeType": node_type,
            "code": f"{node_key}.fields",
            "message": f"{node_key} uses LLM-dependent information collection, which is not available in Runtime V2",
            "category": "node_contract_invalid",
            "reason": reason,
        }
    return {
        "nodeKey": node_key,
        "nodeType": node_type,
        "code": f"{node_key}.type",
        "message": f"{node_key} uses node type {node_type}, which is not available in Runtime V2",
        "category": "unsupported_node_type",
        "reason": reason,
    }


def _runtime_v2_compatibility_error_message(compatibility: Mapping[str, Any]) -> str:
    errors = compatibility.get("errors")
    if isinstance(errors, list) and errors:
        first = errors[0]
        if isinstance(first, Mapping):
            return f"Runtime V2 graph is not compatible: {first.get('message') or first.get('code')}"
    return "Runtime V2 graph is not compatible; run compatibility check for details"


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
        runtime_job_repository: RuntimeJobRepository | None = None,
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
        self._runtime_job_repository = runtime_job_repository
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
            raise BizError(ErrorCode.BAD_REQUEST, _runtime_v2_compatibility_error_message(compatibility))
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
                "ownerId": chatflow_id,
                "statusRef": f"/api/v1/runtime-runs/{run_id}",
                "eventsRef": f"/api/v1/runtime-runs/{run_id}/events",
                "eventStreamRef": f"/api/v1/runtime-runs/{run_id}/events/stream?afterSequence=0",
                "nodesRef": f"/api/v1/runtime-runs/{run_id}/nodes",
                "resultRef": f"/api/v1/runtime-runs/{run_id}/result",
                _owner_id_payload_key(self._owner_type): chatflow_id,
                "input": input_data,
                "idempotencyKey": idempotency_key or "",
                **_definition_payload(definition),
            },
        )
        if self._use_chatflow_session and self._owner_type == "CHATFLOW":
            user_message = _chatflow_user_message_from_input(input_data)
            if user_message:
                self._append_event(
                    session_id=session_id,
                    chatflow_id=chatflow_id,
                    run_id=run_id,
                    event_type="user_message",
                    payload={
                        "role": "user",
                        "content": user_message,
                        "metadata": input_data.get("metadata") if isinstance(input_data.get("metadata"), dict) else {},
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
        existing_node_runs = self._repository.list_node_runs(run_id)
        node_key = _resume_node_key_from_completed_runs(
            existing_node_runs,
            edges,
            nodes,
            context,
            _next_node_key(edges, "start") if existing_node_runs else None,
        )
        try:
            output = self._run_from_node(
                chatflow_id=chatflow_id,
                run_id=run_id,
                session_id=session_id,
                node_key=node_key,
                context=context,
                input_data=input_data,
                nodes=nodes,
                edges=edges,
            )
        except _RuntimeV2Cancelled:
            return
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
        node_runs = self._repository.list_node_runs(run_id)
        output = _resolve_final_output(self._owner_type, output, node_runs)
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
        if self._use_chatflow_session and self._owner_type == "CHATFLOW":
            assistant_message = _chatflow_answer_from_output(output)
            if assistant_message:
                self._append_event(
                    session_id=session_id,
                    chatflow_id=chatflow_id,
                    run_id=run_id,
                    event_type="assistant_message",
                    payload={
                        "role": "assistant",
                        "content": assistant_message,
                        "output": output,
                    },
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
        _load_completed_node_run_outputs(context, self._repository.list_node_runs(run_id))
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
        node_runs = self._repository.list_node_runs(run_id)
        output = _resolve_final_output(self._owner_type, output, node_runs)
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

    def cancel_run(
        self,
        run_id: int,
        *,
        reason: str = "cancelled by operator",
        deadline_ms: int = 1000,
    ) -> dict[str, Any]:
        run = self._run_or_404(run_id)
        chatflow_id = int(run["workflow_id"])
        session_id = self._session_id_for_run(chatflow_id, run_id)
        owner_type = self._owner_type_for_run(run)
        run_status = str(run["status"]).upper()
        deadline_ms = max(0, int(deadline_ms))
        deadline_at = datetime.now() + timedelta(milliseconds=deadline_ms)
        if run_status == "CANCELLED":
            result = self.get_result(run_id)
            result["cancellation"] = {
                "applied": False,
                "idempotent": True,
                "previousStatus": "CANCELLED",
                "reason": "Runtime v2 run was already cancelled.",
                "deadlineMs": deadline_ms,
                "deadlineAt": format_datetime(deadline_at),
            }
            return result
        if run_status in _RUNTIME_V2_TERMINAL_STATUSES:
            result = self.get_result(run_id)
            result["cancellation"] = {
                "applied": False,
                "idempotent": False,
                "previousStatus": run_status,
                "reason": "Runtime v2 run is already terminal.",
                "deadlineMs": deadline_ms,
                "deadlineAt": format_datetime(deadline_at),
            }
            return result
        if run_status not in _RUNTIME_V2_CANCELLABLE_STATUSES:
            raise BizError(ErrorCode.BAD_REQUEST, f"Runtime v2 run cannot be cancelled from status {run_status}")
        checkpoint = self._state_repository.get_waiting_checkpoint(chatflow_id, run_id)
        checkpoint_id = int(checkpoint["id"]) if checkpoint is not None else None
        if checkpoint_id is not None:
            self._state_repository.mark_checkpoint_completed(checkpoint_id)
        runtime_job = (
            self._runtime_job_repository.cancel_by_run(run_id, reason=reason)
            if self._runtime_job_repository is not None
            else None
        )
        cancelled_node_keys = self._cancel_active_node_runs(
            chatflow_id=chatflow_id,
            run_id=run_id,
            session_id=session_id,
            reason=reason,
        )
        phase = _runtime_cancel_phase(
            run_status=run_status,
            had_checkpoint=checkpoint_id is not None,
            cancelled_node_keys=cancelled_node_keys,
            runtime_job=runtime_job,
        )
        self._repository.finish_run(run_id, "CANCELLED", output={}, error=reason)
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
                "deadlineMs": deadline_ms,
                "deadlineAt": format_datetime(deadline_at),
                "cancelledNodeKeys": cancelled_node_keys,
                "runtimeJobStatus": runtime_job.get("status") if runtime_job else None,
                "cancellation": {"applied": True, "idempotent": False, "phase": phase},
            },
            checkpoint_id=checkpoint_id,
        )
        result = self.get_result(run_id)
        result["cancellation"] = {
            "applied": True,
            "idempotent": False,
            "previousStatus": run_status,
            "phase": phase,
            "reason": reason,
            "deadlineMs": deadline_ms,
            "deadlineAt": format_datetime(deadline_at),
            "cancelledNodeKeys": cancelled_node_keys,
            "runtimeJobStatus": runtime_job.get("status") if runtime_job else None,
        }
        return result

    def _cancel_active_node_runs(
        self,
        *,
        chatflow_id: int,
        run_id: int,
        session_id: str,
        reason: str,
    ) -> list[str]:
        cancelled: list[str] = []
        for row in self._repository.list_node_runs(run_id):
            status = str(row.get("status") or "").upper()
            if status not in {"RUNNING", "WAITING"}:
                continue
            if self._cancel_node_run_if_active(
                chatflow_id=chatflow_id,
                run_id=run_id,
                session_id=session_id,
                node_run=row,
                reason=reason,
            ):
                cancelled.append(str(row.get("node_key") or ""))
        return [node_key for node_key in cancelled if node_key]

    def _cancel_node_run_if_active(
        self,
        *,
        chatflow_id: int,
        run_id: int,
        session_id: str,
        node_run: Mapping[str, Any],
        reason: str,
    ) -> bool:
        status = str(node_run.get("status") or "").upper()
        if status == "CANCELLED":
            return False
        if status not in {"RUNNING", "WAITING"}:
            return False
        node_run_id = int(node_run["id"])
        node_key = str(node_run.get("node_key") or "")
        node_type = str(node_run.get("node_type") or "")
        self._repository.finish_node_run(node_run_id, "CANCELLED", {}, error=reason)
        self._append_event(
            session_id=session_id,
            chatflow_id=chatflow_id,
            run_id=run_id,
            event_type="workflow_node_cancelled",
            node_key=node_key,
            payload={"nodeType": node_type, "nodeRunId": node_run_id, "reason": reason},
        )
        self._append_event(
            session_id=session_id,
            chatflow_id=chatflow_id,
            run_id=run_id,
            event_type="node_status_changed",
            node_key=node_key,
            payload={"nodeType": node_type, "nodeRunId": node_run_id, "status": "CANCELLED"},
        )
        return True

    def _raise_if_run_cancelled(
        self,
        *,
        run_id: int,
        chatflow_id: int,
        session_id: str,
        node_run_id: int | None = None,
        reason: str = "cancelled by operator",
    ) -> None:
        if not self._run_has_status(run_id, "CANCELLED"):
            return
        if node_run_id is not None:
            node_run = next(
                (row for row in self._repository.list_node_runs(run_id) if int(row["id"]) == int(node_run_id)),
                None,
            )
            if node_run is not None:
                self._cancel_node_run_if_active(
                    chatflow_id=chatflow_id,
                    run_id=run_id,
                    session_id=session_id,
                    node_run=node_run,
                    reason=reason,
                )
        raise _RuntimeV2Cancelled()

    def get_result(self, run_id: int) -> dict[str, Any]:
        run = self._run_or_404(run_id)
        chatflow_id = int(run["workflow_id"])
        owner_type = self._owner_type_for_run(run)
        runtime_metadata = _runtime_metadata(dict(run.get("input") or {}))
        session_id = self._session_id_for_run(chatflow_id, run_id)
        checkpoint = self._state_repository.get_waiting_checkpoint(chatflow_id, run_id)
        node_runs = self._repository.list_node_runs(run_id)
        events = self._state_repository.list_events(chatflow_id, run_id)
        output = dict(run.get("output") or {})
        waiting_nodes = _runtime_waiting_nodes(run, node_runs, checkpoint)
        refs = {
            "statusRef": f"/api/v1/runtime-runs/{run_id}",
            "eventsRef": f"/api/v1/runtime-runs/{run_id}/events",
            "eventStreamRef": f"/api/v1/runtime-runs/{run_id}/events/stream?afterSequence=0",
            "nodesRef": f"/api/v1/runtime-runs/{run_id}/nodes",
            "resultRef": f"/api/v1/runtime-runs/{run_id}/result",
        }
        result = {
            "runId": run_id,
            "ownerType": owner_type,
            "ownerId": chatflow_id,
            "sessionId": session_id,
            "status": str(run["status"]),
            "result": output,
            "output": output,
            "error": str(run.get("error") or ""),
            "latencyMs": _runtime_result_latency_ms(run, node_runs),
            "usage": _runtime_usage_summary(node_runs),
            "retryable": _runtime_result_retryable(run),
            "events": [_format_runtime_event_summary(event) for event in events],
            "checkpoint": _format_runtime_checkpoint(checkpoint),
            "waitingNodes": waiting_nodes,
            "waitingNodeKeys": [node["nodeKey"] for node in waiting_nodes],
            **refs,
            "runtimeRefs": {"runId": run_id, **refs},
        }
        if self._use_chatflow_session and owner_type == "CHATFLOW":
            session = self._state_repository.get_session(chatflow_id, session_id)
            if session is not None:
                result["conversationId"] = str(session.get("conversation_id") or "")
                result["userId"] = str(session.get("user_id") or "")
                result["channel"] = str(session.get("channel") or "")
                result["variables"] = dict(session.get("variables") or {})
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
        previous_node_runs = self._repository.list_node_runs(run_id)
        completed = _completed_node_keys(previous_node_runs)
        completed.add("start")
        selected_ports = _selected_ports_from_completed_node_runs(edge_rows, node_rows, previous_node_runs)
        forced_next = [node_key] if node_key else []
        output: dict[str, Any] = {}
        parallel_wave_index = 0
        while True:
            self._raise_if_run_cancelled(run_id=run_id, chatflow_id=chatflow_id, session_id=session_id)
            frontier = _runtime_frontier(
                nodes=node_rows,
                edges=edge_rows,
                selected_ports=selected_ports,
                completed_node_keys=completed,
            )
            current_wave = forced_next or _frontier_node_keys(frontier, completed_node_keys=completed)
            forced_next = []
            if not current_wave:
                break
            state_by_node_key = frontier.get("stateByNodeKey") if isinstance(frontier, Mapping) else {}
            wave_results: list[tuple[str, dict[str, Any], dict[str, Any], str]] = []
            wave_items: list[tuple[str, dict[str, Any], dict[str, Any] | None]] = []
            for current in current_wave:
                node = nodes_by_key.get(current)
                if node is None:
                    raise ValueError(f"Runtime v2 node is not in definition: {current}")
                selection_state = None
                if isinstance(state_by_node_key, Mapping) and isinstance(state_by_node_key.get(current), Mapping):
                    selection_state = dict(state_by_node_key[current])
                wave_items.append((current, node, selection_state))
            prestarted: dict[str, tuple[int, float]] = {}
            wave_node_types = {str(node["type"]).upper() for _, node, _ in wave_items}
            prestart_wave = len(wave_items) > 1 and wave_node_types.issubset(_RUNTIME_V2_PRESTART_WAVE_NODE_TYPES)
            parallel_wave = prestart_wave and wave_node_types.issubset(_RUNTIME_V2_PARALLEL_WAVE_NODE_TYPES)
            if parallel_wave:
                parallel_wave_index += 1
                wave_key = f"wave-{run_id}-{parallel_wave_index}"
                wave_items = [
                    (current, node, _selection_state_with_parallel_wave_key(selection_state, wave_key))
                    for current, node, selection_state in wave_items
                ]
            if prestart_wave:
                for current, node, selection_state in wave_items:
                    self._raise_if_run_cancelled(run_id=run_id, chatflow_id=chatflow_id, session_id=session_id)
                    prestarted[current] = self._start_runtime_node_execution(
                        chatflow_id=chatflow_id,
                        run_id=run_id,
                        session_id=session_id,
                        node=node,
                        input_data=input_data,
                        selection_state=selection_state,
                    )
            wave_errors: list[Exception] = []
            if parallel_wave:
                wave_results, wave_errors = self._execute_prestarted_parallel_wave(
                    chatflow_id=chatflow_id,
                    run_id=run_id,
                    session_id=session_id,
                    context=context,
                    input_data=input_data,
                    wave_items=wave_items,
                    prestarted=prestarted,
                )
            else:
                for current, node, selection_state in wave_items:
                    self._raise_if_run_cancelled(run_id=run_id, chatflow_id=chatflow_id, session_id=session_id)
                    node_context = _clone_context_for_frontier_node(context) if len(current_wave) > 1 else context
                    node_run_id, node_started_at = prestarted.get(current, (None, None))
                    try:
                        node_output = self._execute_node(
                            chatflow_id,
                            run_id,
                            session_id,
                            node,
                            node_context,
                            input_data,
                            selection_state=selection_state,
                            node_run_id=node_run_id,
                            started_at=node_started_at,
                        )
                    except Exception as exc:
                        if not prestart_wave:
                            raise
                        wave_errors.append(exc)
                        continue
                    wave_results.append((current, node_output, node, str(node["type"]).upper()))
            for current, node_output, node, node_type in wave_results:
                context.set_output(current, node_output)
                output = node_output
                completed.add(current)
                selected = _selected_port_keys_for_node(edge_rows, current, node_output, node_type)
                if selected is not None:
                    selected_ports[current] = selected
            if wave_errors:
                raise wave_errors[0]
        return output

    def _execute_prestarted_parallel_wave(
        self,
        *,
        chatflow_id: int,
        run_id: int,
        session_id: str,
        context: ExecutionContext,
        input_data: dict[str, Any],
        wave_items: list[tuple[str, dict[str, Any], dict[str, Any] | None]],
        prestarted: dict[str, tuple[int, float]],
    ) -> tuple[list[tuple[str, dict[str, Any], dict[str, Any], str]], list[Exception]]:
        wave_results: list[tuple[str, dict[str, Any], dict[str, Any], str]] = []
        wave_errors: list[Exception] = []
        futures: dict[Future[dict[str, Any]], tuple[str, dict[str, Any], ExecutionContext, int, float]] = {}
        api_resource_rows = self._preload_parallel_api_resource_rows(wave_items)
        with ThreadPoolExecutor(max_workers=max(1, len(wave_items))) as executor:
            for current, node, _selection_state in wave_items:
                self._raise_if_run_cancelled(run_id=run_id, chatflow_id=chatflow_id, session_id=session_id)
                node_run_id, node_started_at = prestarted[current]
                node_context = _clone_context_for_frontier_node(context)
                future = executor.submit(
                    self._execute_parallel_node_operation,
                    chatflow_id,
                    node,
                    node_context,
                    node_run_id,
                    api_resource_rows,
                )
                futures[future] = (current, node, node_context, node_run_id, node_started_at)
            for future in as_completed(futures):
                current, node, _node_context, node_run_id, node_started_at = futures[future]
                node_type = str(node["type"]).upper()
                try:
                    node_output = future.result()
                    node_output = self._complete_prestarted_node_success(
                        chatflow_id=chatflow_id,
                        run_id=run_id,
                        session_id=session_id,
                        node=node,
                        node_run_id=node_run_id,
                        started_at=node_started_at,
                        output=node_output,
                    )
                except Exception as exc:
                    try:
                        handled_output = self._complete_prestarted_node_error(
                            chatflow_id=chatflow_id,
                            run_id=run_id,
                            session_id=session_id,
                            node=node,
                            node_run_id=node_run_id,
                            started_at=node_started_at,
                            exc=exc,
                        )
                    except Exception as completed_exc:
                        wave_errors.append(completed_exc)
                        continue
                    wave_results.append((current, handled_output, node, node_type))
                    continue
                wave_results.append((current, node_output, node, node_type))
        return wave_results, wave_errors

    def _preload_parallel_api_resource_rows(
        self,
        wave_items: list[tuple[str, dict[str, Any], dict[str, Any] | None]],
    ) -> dict[str, dict[str, Any]]:
        if self._api_tool_executor is None:
            return {}
        resource_row = getattr(self._api_tool_executor, "_resource_row", None)
        if not callable(resource_row):
            return {}
        rows: dict[str, dict[str, Any]] = {}
        for _current, node, _selection_state in wave_items:
            if str(node.get("type") or "").upper() != "API_CALL":
                continue
            config = dict(node.get("config") or {})
            resource_id = str(config.get("resourceId") or config.get("resource_id") or "").strip()
            cache_key = _api_resource_cache_key(resource_id)
            if not cache_key or cache_key in rows:
                continue
            rows[cache_key] = dict(resource_row(int(cache_key)))
        return rows

    def _start_runtime_node_execution(
        self,
        *,
        chatflow_id: int,
        run_id: int,
        session_id: str,
        node: dict[str, Any],
        input_data: dict[str, Any],
        selection_state: dict[str, Any] | None = None,
    ) -> tuple[int, float]:
        node_key = str(node["node_key"])
        node_type = str(node["type"]).upper()
        started_at = time.perf_counter()
        node_run_id = self._repository.create_node_run(
            run_id,
            node_key,
            node_type,
            inputs=input_data,
            selection_state=selection_state,
        )
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
        return node_run_id, started_at

    def _execute_node(
        self,
        chatflow_id: int,
        run_id: int,
        session_id: str,
        node: dict[str, Any],
        context: ExecutionContext,
        input_data: dict[str, Any],
        selection_state: dict[str, Any] | None = None,
        node_run_id: int | None = None,
        started_at: float | None = None,
    ) -> dict[str, Any]:
        node_key = str(node["node_key"])
        node_type = str(node["type"]).upper()
        if node_run_id is None:
            node_run_id, started_at = self._start_runtime_node_execution(
                chatflow_id=chatflow_id,
                run_id=run_id,
                session_id=session_id,
                node=node,
                input_data=input_data,
                selection_state=selection_state,
            )
        if started_at is None:
            started_at = time.perf_counter()
        self._raise_if_run_cancelled(
            run_id=run_id,
            chatflow_id=chatflow_id,
            session_id=session_id,
            node_run_id=node_run_id,
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
                output = self._execute_governed_external_node(
                    node=node,
                    node_run_id=node_run_id,
                    operation=lambda: LlmNodeExecutor(
                        self._llm_completer_for(chatflow_id),
                        self._knowledge_facade,
                        self._mcp_tool_executor,
                    ).execute(node, context),
                )
            elif node_type == "KNOWLEDGE":
                if self._knowledge_facade is None:
                    raise ValueError("Runtime v2 KNOWLEDGE node requires KnowledgeFacade")
                output = self._execute_governed_external_node(
                    node=node,
                    node_run_id=node_run_id,
                    operation=lambda: KnowledgeNodeExecutor(self._knowledge_facade).execute(node, context),
                )
            elif node_type == "API_CALL":
                reason = _runtime_v2_api_call_unsupported_reason(dict(node.get("config") or {}))
                if reason:
                    error = _runtime_v2_unsupported_node_error(
                        {"nodeKey": node_key, "nodeType": node_type, "reason": reason}
                    )
                    raise ValueError(error["message"])
                output = self._execute_governed_external_node(
                    node=node,
                    node_run_id=node_run_id,
                    operation=lambda: ApiCallNodeExecutor(self._api_tool_executor).execute(node, context),
                )
                output = _with_runtime_v2_execution_evidence_defaults(output)
            elif node_type == "TOOL_CALL":
                reason = _runtime_v2_tool_call_unsupported_reason(dict(node.get("config") or {}))
                if reason:
                    error = _runtime_v2_unsupported_node_error(
                        {"nodeKey": node_key, "nodeType": node_type, "reason": reason}
                    )
                    raise ValueError(error["message"])
                output = self._execute_governed_external_node(
                    node=node,
                    node_run_id=node_run_id,
                    operation=lambda: ToolCallNodeExecutor(self._mcp_tool_executor, self._api_tool_executor).execute(
                        node, context
                    ),
                )
                output = _with_runtime_v2_execution_evidence_defaults(output)
            elif node_type == "EXECUTE_WORKFLOW":
                output = self._execute_workflow_output(chatflow_id, node, context)
            elif node_type == "TRANSFER_TO_HUMAN":
                output = self._transfer_to_human_output(
                    chatflow_id,
                    run_id,
                    session_id,
                    node,
                    context,
                    input_data,
                    node_run_id,
                )
            elif node_type == "AGENT_CALL":
                output = AgentCallNodeExecutor(self._agent_invoker_for(chatflow_id)).execute(node, context)
            elif node_type == "END":
                output = EndNodeExecutor().execute(node, context)
            else:
                raise ValueError(f"Runtime v2 core coverage is missing node type: {node_type}")
        except _RuntimeV2Interrupt as interrupted:
            self._repository.finish_node_run(node_run_id, "WAITING", interrupted.output)
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
            if isinstance(exc, ExternalCallGovernanceError):
                payload = {**exc.event_payload, "nodeType": node_type, "nodeRunId": node_run_id}
                self._append_event(
                    session_id=session_id,
                    chatflow_id=chatflow_id,
                    run_id=run_id,
                    event_type=exc.event_type,
                    node_key=node_key,
                    payload=payload,
                )
            handled_output = _runtime_v2_handled_error_output(node_type, node, exc, started_at)
            if handled_output is not None:
                handled_output = _with_runtime_v2_side_effect_protection(
                    handled_output,
                    run_id=run_id,
                    node_run_id=node_run_id,
                    node_key=node_key,
                    node_type=node_type,
                )
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
        output = _with_runtime_v2_side_effect_protection(
            output,
            run_id=run_id,
            node_run_id=node_run_id,
            node_key=node_key,
            node_type=node_type,
        )
        self._raise_if_run_cancelled(
            run_id=run_id,
            chatflow_id=chatflow_id,
            session_id=session_id,
            node_run_id=node_run_id,
        )
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

    def _execute_parallel_node_operation(
        self,
        chatflow_id: int,
        node: dict[str, Any],
        context: ExecutionContext,
        node_run_id: int,
        api_resource_rows: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        node_key = str(node["node_key"])
        node_type = str(node["type"]).upper()
        if node_type == "LLM":
            return self._execute_governed_external_node(
                node=node,
                node_run_id=node_run_id,
                operation=lambda: LlmNodeExecutor(
                    self._llm_completer_for(chatflow_id),
                    self._knowledge_facade,
                    self._mcp_tool_executor,
                ).execute(node, context),
            )
        if node_type == "KNOWLEDGE":
            if self._knowledge_facade is None:
                raise ValueError("Runtime v2 KNOWLEDGE node requires KnowledgeFacade")
            return self._execute_governed_external_node(
                node=node,
                node_run_id=node_run_id,
                operation=lambda: KnowledgeNodeExecutor(self._knowledge_facade).execute(node, context),
            )
        if node_type == "API_CALL":
            reason = _runtime_v2_api_call_unsupported_reason(dict(node.get("config") or {}))
            if reason:
                error = _runtime_v2_unsupported_node_error(
                    {"nodeKey": node_key, "nodeType": node_type, "reason": reason}
                )
                raise ValueError(error["message"])
            output = self._execute_governed_external_node(
                node=node,
                node_run_id=node_run_id,
                operation=lambda: ApiCallNodeExecutor(
                    _PreloadedApiResourceExecutor(self._api_tool_executor, api_resource_rows)
                    if self._api_tool_executor is not None and api_resource_rows
                    else self._api_tool_executor
                ).execute(node, context),
            )
            return _with_runtime_v2_execution_evidence_defaults(output)
        if node_type == "TOOL_CALL":
            reason = _runtime_v2_tool_call_unsupported_reason(dict(node.get("config") or {}))
            if reason:
                error = _runtime_v2_unsupported_node_error(
                    {"nodeKey": node_key, "nodeType": node_type, "reason": reason}
                )
                raise ValueError(error["message"])
            output = self._execute_governed_external_node(
                node=node,
                node_run_id=node_run_id,
                operation=lambda: ToolCallNodeExecutor(self._mcp_tool_executor, self._api_tool_executor).execute(
                    node, context
                ),
            )
            return _with_runtime_v2_execution_evidence_defaults(output)
        if node_type == "AGENT_CALL":
            return AgentCallNodeExecutor(self._agent_invoker_for(chatflow_id)).execute(node, context)
        raise ValueError(f"Runtime v2 node is not eligible for parallel wave execution: {node_type}")

    def _complete_prestarted_node_success(
        self,
        *,
        chatflow_id: int,
        run_id: int,
        session_id: str,
        node: dict[str, Any],
        node_run_id: int,
        started_at: float,
        output: dict[str, Any],
    ) -> dict[str, Any]:
        node_key = str(node["node_key"])
        node_type = str(node["type"]).upper()
        output = _with_runtime_v2_side_effect_protection(
            output,
            run_id=run_id,
            node_run_id=node_run_id,
            node_key=node_key,
            node_type=node_type,
        )
        self._raise_if_run_cancelled(
            run_id=run_id,
            chatflow_id=chatflow_id,
            session_id=session_id,
            node_run_id=node_run_id,
        )
        elapsed_ms = max(0, int((time.perf_counter() - started_at) * 1000))
        self._repository.finish_node_run(node_run_id, "SUCCEEDED", output, elapsed_ms=elapsed_ms)
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

    def _complete_prestarted_node_error(
        self,
        *,
        chatflow_id: int,
        run_id: int,
        session_id: str,
        node: dict[str, Any],
        node_run_id: int,
        started_at: float,
        exc: Exception,
    ) -> dict[str, Any]:
        node_key = str(node["node_key"])
        node_type = str(node["type"]).upper()
        if isinstance(exc, ExternalCallGovernanceError):
            payload = {**exc.event_payload, "nodeType": node_type, "nodeRunId": node_run_id}
            self._append_event(
                session_id=session_id,
                chatflow_id=chatflow_id,
                run_id=run_id,
                event_type=exc.event_type,
                node_key=node_key,
                payload=payload,
            )
        handled_output = _runtime_v2_handled_error_output(node_type, node, exc, started_at)
        if handled_output is not None:
            handled_output = _with_runtime_v2_side_effect_protection(
                handled_output,
                run_id=run_id,
                node_run_id=node_run_id,
                node_key=node_key,
                node_type=node_type,
            )
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
        raise exc

    def _execute_governed_external_node(
        self,
        *,
        node: dict[str, Any],
        node_run_id: int | None,
        operation: Callable[[], dict[str, Any]],
    ) -> dict[str, Any]:
        config = dict(node.get("config") or {})
        node_type = str(node.get("type") or "")
        node_key = str(node.get("node_key") or node.get("nodeKey") or "")
        return _RUNTIME_EXTERNAL_CALL_GOVERNANCE.run(
            call_type=_runtime_external_call_type(node_type),
            provider_key=_runtime_external_provider_key(node_type, config),
            node_key=node_key,
            node_run_id=node_run_id,
            policy=external_call_policy_from_config(config),
            operation=operation,
        )

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
        node_run_id: int,
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
        protection = _runtime_v2_side_effect_protection(
            run_id=run_id,
            node_run_id=node_run_id,
            node_key=node_key,
            node_type="TRANSFER_TO_HUMAN",
        )
        proposed_action = {
            "actionType": "transfer_to_human",
            "status": "PENDING",
            "idempotencyKey": protection["idempotencyKey"],
            "handoffId": handoff_id,
            "queue": queue,
            "priority": priority,
            "reason": reason,
        }
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
            "sideEffectProtection": protection,
            "proposedAction": proposed_action,
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
                "idempotencyKey": protection["idempotencyKey"],
                "sideEffectProtection": protection,
                "proposedAction": proposed_action,
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
                "sideEffectProtection": protection,
                "proposedAction": proposed_action,
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
        checkpoint_input = _checkpoint_execution_input(input_data, output)
        checkpoint = self._state_repository.create_checkpoint(
            session_id=session_id,
            chatflow_id=chatflow_id,
            run_id=run_id,
            pending_node_key=node_key,
            execution_context={"input": checkpoint_input},
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
        event_payload.setdefault("ownerType", self._owner_type)
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
        self._repository.session.rollback()
        self._repository.session.expire_all()
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
        runtime_job_repository: RuntimeJobRepository | None = None,
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
            runtime_job_repository=runtime_job_repository,
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
        selection_state: dict[str, Any] | None = None,
    ) -> int:
        return self._base.create_node_run(
            workflow_run_id,
            node_key,
            node_type,
            inputs=inputs,
            selection_state=selection_state,
        )

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


class _RuntimeV2Cancelled(Exception):
    pass


def _start_payload(start: RuntimeV2Start) -> dict[str, Any]:
    refs = RuntimeV2RefBuilder.build(owner_type=start.owner_type, owner_id=start.owner_id, run_id=start.run_id)
    payload = {
        "runId": start.run_id,
        "ownerType": start.owner_type,
        "ownerId": start.owner_id,
        "sessionId": start.session_id,
        "status": start.status,
        "statusRef": refs["statusRef"],
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


def _chatflow_user_message_from_input(input_data: dict[str, Any]) -> str:
    for key in ("sys.query", "USER_INPUT", "userMessage", "message", "query", "content"):
        value = input_data.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return ""


def _chatflow_answer_from_output(output: dict[str, Any]) -> str:
    if _is_explicit_no_reply_output(output):
        return ""
    return _visible_text_from_output(output, allow_any_string=True)


_CHATFLOW_REPLY_KEYS = ("answer", "final", "output", "content", "message", "text")
_PRIORITY_REPLY_KEYS = ("replyPriority", "reply_priority", "priorityReply", "priority_reply")


def _resolve_final_output(
    owner_type: str,
    output: dict[str, Any],
    node_runs: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized_owner = owner_type.upper()
    if normalized_owner == "CHATFLOW":
        return _resolve_chatflow_final_output(output, node_runs)
    if _is_side_effect_only_output(output):
        summary = _side_effect_only_summary(normalized_owner, node_runs)
        if summary:
            return summary
    return output


def _resolve_chatflow_final_output(
    output: dict[str, Any],
    node_runs: list[dict[str, Any]],
) -> dict[str, Any]:
    end_output = _latest_node_output(node_runs, "END")
    if end_output is not None and _visible_text_from_output(end_output, allow_any_string=True):
        return end_output
    answer_output = _answer_mapping_output(node_runs)
    if answer_output is not None:
        return answer_output
    priority_output = _priority_reply_output(node_runs)
    if priority_output is not None:
        return priority_output
    if _is_side_effect_only_output(output):
        summary = _side_effect_only_summary("CHATFLOW", node_runs)
        if summary:
            return summary
    return output


def _latest_node_output(node_runs: list[dict[str, Any]], node_type: str) -> dict[str, Any] | None:
    for row in reversed(node_runs):
        if str(row.get("node_type") or "").upper() == node_type.upper():
            return _node_run_outputs(row)
    return None


def _answer_mapping_output(node_runs: list[dict[str, Any]]) -> dict[str, Any] | None:
    for row in reversed(node_runs):
        if str(row.get("node_type") or "").upper() == "END":
            continue
        output = _node_run_outputs(row)
        if _is_side_effect_only_output(output):
            continue
        if _reply_priority(output) is not None:
            continue
        value = output.get("answer")
        if _non_empty_text(value):
            return {"answer": str(value)}
    return None


def _priority_reply_output(node_runs: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates: list[tuple[float, int, dict[str, Any]]] = []
    for index, row in enumerate(node_runs):
        if str(row.get("node_type") or "").upper() == "END":
            continue
        output = _node_run_outputs(row)
        if _is_side_effect_only_output(output):
            continue
        priority = _reply_priority(output)
        if priority is None:
            continue
        if not _visible_text_from_output(output, allow_any_string=False):
            continue
        candidates.append((priority, index, output))
    if not candidates:
        return None
    _, _, output = max(candidates, key=lambda item: (item[0], item[1]))
    return dict(output)


def _side_effect_only_summary(owner_type: str, node_runs: list[dict[str, Any]]) -> dict[str, Any]:
    evidence: list[dict[str, Any]] = []
    for row in node_runs:
        output = _node_run_outputs(row)
        if not _is_side_effect_only_output(output):
            continue
        item = {
            "nodeKey": str(row.get("node_key") or ""),
            "nodeType": str(row.get("node_type") or ""),
            "status": str(row.get("status") or ""),
            "output": output,
        }
        if "sideEffectEvidence" in output:
            item["sideEffectEvidence"] = output["sideEffectEvidence"]
        evidence.append(item)
    if not evidence:
        return {}
    summary: dict[str, Any] = {
        "sideEffectOnly": True,
        "summary": "side_effect_only_completed",
        "sideEffectEvidence": evidence,
    }
    if owner_type.upper() == "CHATFLOW":
        summary["noReply"] = True
    return summary


def _node_run_outputs(row: Mapping[str, Any]) -> dict[str, Any]:
    output = row.get("outputs")
    return dict(output) if isinstance(output, dict) else {}


def _visible_text_from_output(output: Mapping[str, Any], *, allow_any_string: bool) -> str:
    for key in _CHATFLOW_REPLY_KEYS:
        value = output.get(key)
        if _non_empty_text(value):
            return str(value)
    if allow_any_string:
        for value in output.values():
            if isinstance(value, str) and value.strip():
                return value
    return ""


def _reply_priority(output: Mapping[str, Any]) -> float | None:
    for key in _PRIORITY_REPLY_KEYS:
        if key not in output:
            continue
        try:
            return float(output[key])
        except (TypeError, ValueError):
            return None
    return None


def _is_explicit_no_reply_output(output: Mapping[str, Any]) -> bool:
    if _truthy_output_flag(output.get("noReply") or output.get("no_reply")):
        return True
    return _is_side_effect_only_output(output) and str(output.get("summary") or "") == "side_effect_only_completed"


def _is_side_effect_only_output(output: Mapping[str, Any]) -> bool:
    return _truthy_output_flag(output.get("sideEffectOnly") or output.get("side_effect_only"))


def _truthy_output_flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _non_empty_text(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


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


def _runtime_frontier(
    *,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    selected_ports: dict[str, list[str]],
    completed_node_keys: set[str],
) -> dict[str, Any]:
    return compute_frontier(
        {"nodes": nodes, "edges": edges},
        {"selectedPorts": selected_ports, "completedNodeKeys": completed_node_keys},
    )


def _next_frontier_node_keys(
    *,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    selected_ports: dict[str, list[str]],
    completed_node_keys: set[str],
) -> list[str]:
    frontier = _runtime_frontier(
        nodes=nodes,
        edges=edges,
        selected_ports=selected_ports,
        completed_node_keys=completed_node_keys,
    )
    return _frontier_node_keys(frontier, completed_node_keys=completed_node_keys)


def _frontier_node_keys(frontier: Mapping[str, Any], *, completed_node_keys: set[str]) -> list[str]:
    node_keys: list[str] = []
    for node_key in frontier.get("runnableNodeKeys") or []:
        text = str(node_key)
        if text != "start" and text not in completed_node_keys:
            node_keys.append(text)
    return node_keys


def _clone_context_for_frontier_node(context: ExecutionContext) -> ExecutionContext:
    cloned = ExecutionContext()
    cloned.load_scopes(context.scopes_snapshot())
    for node_key, output in context.outputs_snapshot().items():
        cloned.set_output(node_key, output)
    return cloned


def _selection_state_with_parallel_wave_key(
    selection_state: dict[str, Any] | None,
    wave_key: str,
) -> dict[str, Any]:
    payload = dict(selection_state or {})
    payload["parallelWaveKey"] = wave_key
    return payload


def _completed_node_keys(node_runs: list[dict[str, Any]]) -> set[str]:
    return {
        str(row.get("node_key") or "")
        for row in node_runs
        if _node_run_status_is_completed(row.get("status")) and str(row.get("node_key") or "")
    }


def _selected_ports_from_completed_node_runs(
    edges: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
    node_runs: list[dict[str, Any]],
) -> dict[str, list[str]]:
    node_types = {str(node.get("node_key") or node.get("nodeKey") or ""): str(node.get("type") or "").upper() for node in nodes}
    selected_ports: dict[str, list[str]] = {}
    for node in nodes:
        node_key = str(node.get("node_key") or node.get("nodeKey") or "")
        node_type = str(node.get("type") or "").upper()
        if node_key == "start" or node_type == "START":
            if _runtime_v2_allows_default_fanout(dict(node.get("config") or {})):
                selected_ports.setdefault(node_key, ["default"])
    for row in node_runs:
        if not _node_run_status_is_completed(row.get("status")):
            continue
        node_key = str(row.get("node_key") or "")
        outputs = row.get("outputs")
        if not node_key or not isinstance(outputs, dict):
            continue
        selected = _selected_port_keys_for_node(edges, node_key, outputs, node_types.get(node_key, ""))
        if selected is not None:
            selected_ports[node_key] = selected
    return selected_ports


def _selected_port_keys_for_node(
    edges: list[dict[str, Any]],
    source: str,
    output: dict[str, Any],
    node_type: str,
) -> list[str] | None:
    if node_type not in {"CONDITION", "INTENT_RECOGNITION"} and "route" not in output and "branch" not in output:
        return None
    target = _next_node_key(edges, source, output, node_type)
    if target is None:
        return []
    for edge in edges:
        if str(edge.get("source_node_key") or edge.get("sourceNodeKey") or "") != source:
            continue
        if str(edge.get("target_node_key") or edge.get("targetNodeKey") or "") != target:
            continue
        return [_edge_source_port_key(edge)]
    return []


def _edge_source_port_key(edge: Mapping[str, Any]) -> str:
    value = edge.get("source_port_key")
    if value is None:
        value = edge.get("sourcePortKey")
    text = str(value or "").strip()
    if text:
        return text
    condition = edge.get("condition_expr")
    if condition is None:
        condition = edge.get("condition")
    condition_text = str(condition or "").strip()
    return condition_text or "default"


def _resume_node_key_from_completed_runs(
    node_runs: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
    context: ExecutionContext,
    initial_node_key: str | None,
) -> str | None:
    nodes_by_key = {str(node["node_key"]): node for node in nodes}
    completed_outputs: dict[str, dict[str, Any]] = {}
    for row in node_runs:
        if not _node_run_status_is_completed(row.get("status")):
            continue
        node_key = str(row.get("node_key") or "")
        outputs = row.get("outputs")
        if node_key and node_key not in completed_outputs and isinstance(outputs, dict):
            completed_outputs[node_key] = dict(outputs)

    current = initial_node_key
    while current and current in completed_outputs:
        output = completed_outputs[current]
        context.set_output(current, output)
        node = nodes_by_key.get(current)
        current = _next_node_key(edges, current, output, str((node or {}).get("type") or "").upper())
    return current


def _load_completed_node_run_outputs(context: ExecutionContext, node_runs: list[dict[str, Any]]) -> None:
    for row in node_runs:
        if not _node_run_status_is_completed(row.get("status")):
            continue
        node_key = str(row.get("node_key") or "")
        outputs = row.get("outputs")
        if node_key and isinstance(outputs, dict):
            context.set_output(node_key, dict(outputs))


def _node_run_status_is_completed(status: Any) -> bool:
    return str(status or "").upper() in {"COMPLETED", "SUCCEEDED"}


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


def _api_resource_cache_key(resource_id: str) -> str:
    normalized = str(resource_id or "").strip()
    if normalized.isdigit():
        return normalized
    if normalized.startswith("api-resource:"):
        raw = normalized.split(":", 2)[1] if ":" in normalized else ""
        return raw if raw.isdigit() else ""
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


def _runtime_v2_allows_default_fanout(config: dict[str, Any]) -> bool:
    ports = config.get("ports")
    if not isinstance(ports, list):
        return False
    for port in ports:
        if not isinstance(port, Mapping):
            continue
        key = str(port.get("key") or port.get("portKey") or port.get("port_key") or "default")
        if key == "default" and bool(port.get("allowFanOut") or port.get("allow_fan_out")):
            return True
    return False


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
    if error_behavior not in {"continue", "branch", "partial"}:
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
    if error_behavior == "partial":
        output["partialSuccess"] = True
        evidence["partialSuccess"] = True
        evidence["failureStrategy"] = "partial_success"
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


def _with_runtime_v2_side_effect_protection(
    output: dict[str, Any],
    *,
    run_id: int,
    node_run_id: int,
    node_key: str,
    node_type: str,
) -> dict[str, Any]:
    normalized_type = node_type.upper()
    if normalized_type not in _RUNTIME_V2_SIDE_EFFECT_PROTECTION:
        return output
    protection = _runtime_v2_side_effect_protection(
        run_id=run_id,
        node_run_id=node_run_id,
        node_key=node_key,
        node_type=normalized_type,
    )
    enriched = {**output, "sideEffectProtection": protection}
    evidence = output.get("evidence")
    if isinstance(evidence, Mapping):
        enriched["evidence"] = {
            **dict(evidence),
            "idempotencyKey": protection["idempotencyKey"],
            "sideEffectProtection": protection,
        }
    return enriched


def _runtime_v2_side_effect_protection(
    *,
    run_id: int,
    node_run_id: int,
    node_key: str,
    node_type: str,
) -> dict[str, Any]:
    effect_type, strategy = _RUNTIME_V2_SIDE_EFFECT_PROTECTION[node_type.upper()]
    return {
        "effectType": effect_type,
        "strategy": strategy,
        "idempotencyKey": f"runtime-v2:{run_id}:{node_key}:{node_type.upper()}",
        "executionRecord": {
            "runId": int(run_id),
            "nodeRunId": int(node_run_id),
            "nodeKey": node_key,
            "nodeType": node_type.upper(),
        },
    }


def _checkpoint_execution_input(input_data: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    checkpoint_input = dict(input_data)
    interrupt = output.get("interrupt")
    if not isinstance(interrupt, Mapping):
        return checkpoint_input
    if str(interrupt.get("type") or "").upper() != "INFORMATION_COLLECTION":
        return checkpoint_input
    collected = interrupt.get("collected")
    if not isinstance(collected, Mapping):
        collected = output.get("collected")
    if not isinstance(collected, Mapping):
        return checkpoint_input
    merged = _merge_checkpoint_collected(checkpoint_input.get("collected"), collected)
    checkpoint_input["collected"] = merged
    collection_key = str(interrupt.get("collectionKey") or "").strip()
    if collection_key and collection_key != "collected":
        checkpoint_input[collection_key] = _merge_checkpoint_collected(checkpoint_input.get(collection_key), merged)
    return checkpoint_input


def _merge_checkpoint_collected(previous: Any, current: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(previous) if isinstance(previous, Mapping) else {}
    merged.update(dict(current))
    return merged


def _format_runtime_event(event: dict[str, Any]) -> dict[str, Any]:
    payload = dict(event.get("payload") or {})
    formatted = {
        "id": int(event["id"]),
        "runId": int(event["run_id"]),
        "sequence": int(event["sequence"]),
        "type": str(event["event_type"]),
        "level": str(payload.get("level") or "L1"),
        "source": str(payload.get("source") or _source_from_owner_type(payload.get("ownerType"))),
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


def _format_runtime_event_summary(event: dict[str, Any]) -> dict[str, Any]:
    payload = dict(event.get("payload") or {})
    formatted: dict[str, Any] = {
        "sequence": int(event["sequence"]),
        "type": str(event["event_type"]),
        "status": _runtime_event_node_state(str(event["event_type"]), payload),
        "createdAt": format_datetime(event["created_at"]),
    }
    if event.get("checkpoint_id"):
        formatted["checkpointId"] = int(event["checkpoint_id"])
    return formatted


def _runtime_result_latency_ms(run: Mapping[str, Any], node_runs: list[dict[str, Any]]) -> int:
    elapsed_ms = _runtime_non_negative_int(run.get("elapsed_ms"), 0)
    if elapsed_ms:
        return elapsed_ms
    return sum(_runtime_non_negative_int(row.get("elapsed_ms"), 0) for row in node_runs)


def _runtime_usage_summary(node_runs: list[dict[str, Any]]) -> dict[str, Any]:
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0
    estimated = False
    for row in node_runs:
        outputs = row.get("outputs") if isinstance(row.get("outputs"), Mapping) else {}
        usage = outputs.get("__usage") if isinstance(outputs.get("__usage"), Mapping) else {}
        if not usage:
            continue
        input_value = _runtime_usage_value(usage, "inputTokens", "input_tokens", "promptTokens", "prompt_tokens")
        output_value = _runtime_usage_value(
            usage,
            "outputTokens",
            "output_tokens",
            "completionTokens",
            "completion_tokens",
        )
        total_value = _runtime_usage_value(usage, "totalTokens", "total_tokens")
        input_tokens += input_value
        output_tokens += output_value
        total_tokens += total_value if total_value else input_value + output_value
        estimated = estimated or bool(usage.get("estimated"))
    return {
        "inputTokens": input_tokens,
        "outputTokens": output_tokens,
        "totalTokens": total_tokens,
        "estimated": estimated,
    }


def _runtime_usage_value(usage: Mapping[str, Any], *keys: str) -> int:
    for key in keys:
        value = usage.get(key)
        if value is not None:
            return _runtime_non_negative_int(value, 0)
    return 0


def _runtime_non_negative_int(value: Any, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def _runtime_result_retryable(run: Mapping[str, Any]) -> bool:
    return str(run.get("status") or "").upper() == "FAILED"


def _runtime_cancel_phase(
    *,
    run_status: str,
    had_checkpoint: bool,
    cancelled_node_keys: list[str],
    runtime_job: Mapping[str, Any] | None,
) -> str:
    if cancelled_node_keys:
        return "running"
    if had_checkpoint or run_status == "INTERRUPTED":
        return "waiting"
    if runtime_job is not None:
        return "queued"
    return "scheduled"


def _runtime_external_call_type(node_type: str) -> str:
    normalized = str(node_type or "").upper()
    if normalized == "API_CALL":
        return "API"
    if normalized == "TOOL_CALL":
        return "TOOL"
    if normalized in _RUNTIME_V2_EXTERNAL_CALL_NODE_TYPES:
        return normalized
    return "EXTERNAL"


def _runtime_external_provider_key(node_type: str, config: Mapping[str, Any]) -> str:
    normalized = str(node_type or "").upper()
    if normalized == "LLM":
        return "llm:" + str(config.get("modelConfigId") or config.get("model_config_id") or config.get("model") or "default")
    if normalized == "API_CALL":
        return "api:" + str(config.get("resourceId") or config.get("resource_id") or config.get("url") or config.get("endpoint") or "direct")
    if normalized == "TOOL_CALL":
        return "tool:" + str(config.get("resourceId") or config.get("resource_id") or config.get("toolName") or config.get("name") or "default")
    if normalized == "KNOWLEDGE":
        return "knowledge:" + str(config.get("knowledgeBaseId") or config.get("knowledge_base_id") or "default")
    return "external:" + normalized.lower()


def _runtime_waiting_nodes(
    run: Mapping[str, Any],
    node_runs: list[dict[str, Any]],
    checkpoint: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    if str(run.get("status") or "").upper() not in {"RUNNING", "INTERRUPTED"}:
        return []
    latest_by_node_key: dict[str, dict[str, Any]] = {}
    for row in node_runs:
        node_key = str(row.get("node_key") or "")
        if node_key:
            latest_by_node_key[node_key] = row
    checkpoint_node_key = str((checkpoint or {}).get("pending_node_key") or "")
    waiting_nodes: list[dict[str, Any]] = []
    for node_key, row in latest_by_node_key.items():
        if _node_status(str(row.get("status") or "")) != "WAITING":
            continue
        payload: dict[str, Any] = {
            "nodeKey": node_key,
            "nodeType": str(row.get("node_type") or ""),
            "status": "WAITING",
            "nodeRunId": int(row["id"]),
        }
        if checkpoint_node_key == node_key and checkpoint is not None:
            payload["checkpointId"] = int(checkpoint["id"])
        waiting_nodes.append(payload)
    return waiting_nodes


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
        "selectionState": _runtime_node_selection_state(row),
        "inputs": dict(row.get("inputs") or {}),
        "outputs": dict(row.get("outputs") or {}),
        "error": str(row.get("error") or ""),
        "elapsedMs": int(row.get("elapsed_ms") or 0),
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


def _runtime_node_selection_state(row: Mapping[str, Any]) -> dict[str, Any]:
    raw = row.get("selection_state")
    if isinstance(raw, Mapping):
        node_key = str(raw.get("nodeKey") or raw.get("node_key") or row.get("node_key") or "")
        state = str(raw.get("state") or "").strip().lower()
        selected = raw.get("selectedUpstreamNodeKeys") or raw.get("selected_upstream_node_keys") or []
        skipped = raw.get("skippedUpstreamNodeKeys") or raw.get("skipped_upstream_node_keys") or []
        return {
            "nodeKey": node_key,
            "state": state or _node_selection_state_from_status(str(row.get("status") or "")),
            "selectedUpstreamNodeKeys": list(selected) if isinstance(selected, list) else [],
            "skippedUpstreamNodeKeys": list(skipped) if isinstance(skipped, list) else [],
            "reason": str(raw.get("reason") or ""),
            **_runtime_node_selection_state_extra(raw),
        }
    return {
        "nodeKey": str(row.get("node_key") or ""),
        "state": _node_selection_state_from_status(str(row.get("status") or "")),
        "selectedUpstreamNodeKeys": [],
        "skippedUpstreamNodeKeys": [],
        "reason": "",
    }


def _runtime_node_selection_state_extra(raw: Mapping[str, Any]) -> dict[str, Any]:
    extra: dict[str, Any] = {}
    parallel_wave_key = str(raw.get("parallelWaveKey") or raw.get("parallel_wave_key") or "").strip()
    if parallel_wave_key:
        extra["parallelWaveKey"] = parallel_wave_key
    join = raw.get("join")
    if isinstance(join, Mapping):
        extra["join"] = dict(join)
    return extra


def _node_selection_state_from_status(status: str) -> str:
    return {
        "SUCCEEDED": "completed",
        "COMPLETED": "completed",
        "RUNNING": "running",
        "FAILED": "failed",
        "SKIPPED": "skipped",
        "WAITING": "waiting",
        "CANCELLED": "cancelled",
    }.get(status.upper(), "pending")


def _node_status(status: str) -> str:
    return {
        "SUCCEEDED": "COMPLETED",
        "RUNNING": "RUNNING",
        "FAILED": "FAILED",
        "SKIPPED": "SKIPPED",
        "WAITING": "WAITING",
    }.get(status.upper(), status.upper())


def _source_from_owner_type(owner_type: Any) -> str:
    """Derive runtime event source from owner_type for fallback paths.

    Spec 213.3.5h: CHATFLOW-owned runs emit 'chatflow_runtime_v2',
    WORKFLOW-owned runs emit 'workflow_runtime_v2'. Returns 'runtime_v2'
    when owner_type is absent (legacy compat).
    """
    if not owner_type:
        return "runtime_v2"
    normalized = str(owner_type).strip().upper()
    if normalized in {"CHATFLOW", "WORKFLOW"}:
        return f"{normalized.lower()}_runtime_v2"
    return "runtime_v2"


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
