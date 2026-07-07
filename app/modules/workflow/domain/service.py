from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from time import perf_counter
from time import time_ns
from typing import Any

from app.core.errors import BizError, ErrorCode
from app.core.host.context import RequestContext
from app.modules.audit.infra.repository import AuditRepository
from app.modules.agent.infra.repository import AgentRepository
from app.modules.chat.domain.llm_request import (
    ChatRequestMessage,
    OpenAIChatRequestBuilder,
    ProviderBackedOpenAIChatClient,
    ProviderChatConfig,
)
from app.modules.chat.domain.orchestrator import ChatOrchestrator
from app.modules.chat.domain.tool_runner import McpToolExecutor, ToolExecutionResult
from app.modules.chat.domain.tool_schema import ToolDefinition
from app.modules.chat.domain.service import ChatService
from app.modules.chat.infra.repository import ChatRepository
from app.modules.chat.web.schemas import ChatMessageCreateRequest, ChatSessionCreateRequest
from app.modules.knowledge.api.facade import KnowledgeFacade
from app.modules.provider.api.facade import ProviderModelFacade
from app.modules.provider.api.schemas import ModelConfigDto
from app.modules.provider.infra.llm_adapters import OpenAIAdapterParser
from app.modules.workflow.domain.channel import (
    ChannelInboundRequest,
    channel_shells,
    runnable_channel_adapter,
)
from app.modules.workflow.domain.engine import ApiToolExecutor, WorkflowExecutionEngine, WorkflowExecutionError
from app.modules.workflow.domain.engine import AgentInvocationResult
from app.modules.workflow.domain.engine import WorkflowLlmCompleter
from app.modules.workflow.domain.graph_validation import (
    validate_node_contracts,
    validate_node_endpoints,
    validate_variable_references,
)
from app.modules.workflow.infra.channel_repository import ChatflowChannelRepository
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.publish_repository import WorkflowPublishRepository
from app.modules.workflow.infra.repository import WorkflowRepository
from app.modules.workflow.web.schemas import (
    ChatflowChannelTestRequest,
    ChatflowChannelUpdateRequest,
    WorkflowCreateRequest,
    WorkflowDetailResponse,
    WorkflowEdgeResponse,
    WorkflowNodeRunRequest,
    WorkflowNodeRunResponse,
    WorkflowNodeResponse,
    WorkflowPageResponse,
    WorkflowResumeRequest,
    WorkflowRunRequest,
    WorkflowRunResponse,
    WorkflowResponse,
    WorkflowUpdateRequest,
    format_datetime,
)

LlmClientFactory = Callable[[ProviderChatConfig], Any]


class WorkflowService:
    def __init__(
        self,
        repository: WorkflowRepository,
        flow_type: str = "WORKFLOW",
        agent_repository: AgentRepository | None = None,
        model_facade: ProviderModelFacade | None = None,
        knowledge_facade: KnowledgeFacade | None = None,
        request_builder: OpenAIChatRequestBuilder | None = None,
        parser: OpenAIAdapterParser | None = None,
        llm_client_factory: LlmClientFactory | None = None,
        mcp_tool_executor: McpToolExecutor | None = None,
        api_tool_executor: ApiToolExecutor | None = None,
        chatflow_state_repository: ChatflowStateRepository | None = None,
        channel_repository: ChatflowChannelRepository | None = None,
        publish_repository: WorkflowPublishRepository | None = None,
        handoff_service: Any | None = None,
        audit_repository: AuditRepository | None = None,
        request_context: RequestContext | None = None,
        preferred_llm_agent_name: str | None = None,
    ) -> None:
        self._repository = repository
        self._flow_type = flow_type
        self._agent_repository = agent_repository
        self._model_facade = model_facade
        self._knowledge_facade = knowledge_facade
        self._request_builder = request_builder or OpenAIChatRequestBuilder()
        self._parser = parser or OpenAIAdapterParser()
        self._llm_client_factory = llm_client_factory or ProviderBackedOpenAIChatClient
        self._mcp_tool_executor = mcp_tool_executor
        self._api_tool_executor = api_tool_executor
        self._chatflow_state_repository = chatflow_state_repository
        self._channel_repository = channel_repository
        self._publish_repository = publish_repository
        self._handoff_service = handoff_service
        self._audit_repository = audit_repository
        self._request_context = request_context
        self._preferred_llm_agent_name = preferred_llm_agent_name

    def list(self, page: int, page_size: int, status: str | None) -> dict[str, Any]:
        rows, total = self._repository.list_page(page, page_size, status, self._flow_type)
        response = WorkflowPageResponse(
            list=[self._response(row) for row in rows],
            total=total,
            page=page,
            pageSize=page_size,
        )
        return response.model_dump(by_alias=True)

    def create(self, request: WorkflowCreateRequest) -> dict[str, Any]:
        nodes = [node.model_dump() for node in request.nodes]
        _ensure_no_inline_secrets(nodes)
        row = self._repository.create(
            {"name": request.name, "description": request.description, "flow_type": self._flow_type},
            nodes,
            [edge.model_dump() for edge in request.edges],
        )
        return self._detail_response(row).model_dump(by_alias=True)

    def get(self, workflow_id: int) -> dict[str, Any]:
        row = self._repository.get(workflow_id, self._flow_type)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Workflow not found")
        return self._detail_response(row).model_dump(by_alias=True)

    def update(self, workflow_id: int, request: WorkflowUpdateRequest) -> dict[str, Any]:
        values: dict[str, Any] = {}
        if request.name is not None:
            values["name"] = request.name
        if request.description is not None:
            values["description"] = request.description
        if request.status is not None:
            values["status"] = request.status
        nodes = [node.model_dump() for node in request.nodes] if request.nodes is not None else None
        if nodes is not None:
            _ensure_no_inline_secrets(nodes)
        row = self._repository.update(
            workflow_id,
            values,
            nodes,
            [edge.model_dump() for edge in request.edges] if request.edges is not None else None,
            self._flow_type,
        )
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Workflow not found")
        return self._detail_response(row).model_dump(by_alias=True)

    def delete(self, workflow_id: int) -> None:
        if not self._repository.delete(workflow_id, self._flow_type):
            raise BizError(ErrorCode.NOT_FOUND, "Workflow not found")

    def execute(self, workflow_id: int, request: WorkflowRunRequest) -> dict[str, Any]:
        if self._repository.get(workflow_id, self._flow_type) is None:
            raise BizError(ErrorCode.NOT_FOUND, "Workflow not found")
        input_data = dict(request.input)
        if self._flow_type == "CHATFLOW":
            input_data = self._chatflow_runtime_input(workflow_id, input_data)
        try:
            result = WorkflowExecutionEngine(
                self._repository,
                knowledge_facade=self._knowledge_facade_for(workflow_id),
                llm_completer=(
                    self._llm_completer(workflow_id)
                    if self._has_start_node(workflow_id)
                    else None
                ),
                mcp_tool_executor=self._mcp_tool_executor,
                api_tool_executor=self._api_tool_executor,
                agent_invoker=self._agent_invoker_for(workflow_id),
                flow_type=self._flow_type,
                handoff_service=self._handoff_service,
            ).run(workflow_id, input_data)
        except WorkflowExecutionError as exc:
            raise BizError(ErrorCode.BAD_REQUEST, str(exc)) from exc
        response = WorkflowRunResponse(
            runId=result.run_id,
            status=result.status,
            output=result.output,
        )
        data = response.model_dump(by_alias=True)
        if self._flow_type == "CHATFLOW" and self._chatflow_state_repository is not None:
            data.update(self._record_chatflow_state(workflow_id, input_data, result))
        data.update(self._debug_url_fields(workflow_id, result.run_id))
        self._audit(
            f"{self._flow_type}_RUN",
            f"{self._flow_type}_RUN",
            result.run_id,
            metadata={"workflowId": workflow_id, "status": result.status},
        )
        return data

    def run_node(self, workflow_id: int, node_key: str, request: WorkflowNodeRunRequest) -> dict[str, Any]:
        if self._repository.get(workflow_id, self._flow_type) is None:
            raise BizError(ErrorCode.NOT_FOUND, "Workflow not found")
        nodes = self._repository.list_nodes(workflow_id)
        if not any(str(node["node_key"]) == node_key for node in nodes):
            raise BizError(ErrorCode.NOT_FOUND, "Workflow node not found")
        try:
            result = WorkflowExecutionEngine(
                self._repository,
                knowledge_facade=self._knowledge_facade_for(workflow_id),
                llm_completer=self._llm_completer(workflow_id),
                mcp_tool_executor=self._mcp_tool_executor,
                api_tool_executor=self._api_tool_executor,
                agent_invoker=self._agent_invoker_for(workflow_id),
                flow_type=self._flow_type,
                handoff_service=self._handoff_service,
            ).run_node(workflow_id, node_key, dict(request.input))
        except WorkflowExecutionError as exc:
            raise BizError(ErrorCode.BAD_REQUEST, str(exc)) from exc
        response = WorkflowNodeRunResponse(
            nodeKey=result.node_key,
            status=result.status,
            input=result.input,
            output=result.output,
            elapsedMs=result.elapsed_ms,
        )
        return response.model_dump(by_alias=True)

    def list_channels(self, chatflow_id: int) -> dict[str, Any]:
        self._ensure_chatflow_and_channel_repo(chatflow_id)
        assert self._channel_repository is not None
        saved = {str(row["channel_id"]): row for row in self._channel_repository.list_configs(chatflow_id)}
        channels = [self._channel_response(shell, saved.get(shell.channel_id)) for shell in channel_shells()]
        return {"list": channels, "total": len(channels)}

    def update_channel(
        self,
        chatflow_id: int,
        channel_id: str,
        request: ChatflowChannelUpdateRequest,
    ) -> dict[str, Any]:
        self._ensure_chatflow_and_channel_repo(chatflow_id)
        normalized = channel_id.strip().lower()
        shell = next((item for item in channel_shells() if item.channel_id == normalized), None)
        if shell is None:
            raise BizError(ErrorCode.NOT_FOUND, "Chatflow channel not found")
        if not shell.runnable:
            raise BizError(ErrorCode.BAD_REQUEST, f"Channel {normalized} is not available")
        assert self._channel_repository is not None
        row = self._channel_repository.upsert_config(
            chatflow_id=chatflow_id,
            channel_id=normalized,
            display_name=request.display_name.strip() or shell.display_name,
            enabled=bool(request.enabled),
            config=dict(request.config),
        )
        self._audit(
            "CHATFLOW_CHANNEL_UPDATE",
            "CHATFLOW_CHANNEL",
            f"{chatflow_id}:{normalized}",
            metadata={"enabled": bool(request.enabled), "displayName": request.display_name.strip() or shell.display_name},
        )
        return self._channel_response(shell, row)

    def test_channel(
        self,
        chatflow_id: int,
        channel_id: str,
        request: ChatflowChannelTestRequest,
    ) -> dict[str, Any]:
        self._ensure_chatflow_and_channel_repo(chatflow_id)
        normalized = channel_id.strip().lower()
        assert self._channel_repository is not None
        saved = self._channel_repository.get_config(chatflow_id, normalized)
        shell = next((item for item in channel_shells() if item.channel_id == normalized), None)
        if shell is None:
            raise BizError(ErrorCode.NOT_FOUND, "Chatflow channel not found")
        if not shell.runnable:
            message = f"Channel {normalized} is not available: {shell.unavailable_reason}"
            self._channel_failure_audit(chatflow_id, normalized, message)
            raise BizError(ErrorCode.BAD_REQUEST, message)
        if saved is not None and not bool(saved.get("enabled")):
            message = f"Channel {normalized} is disabled"
            self._channel_failure_audit(chatflow_id, normalized, message)
            raise BizError(ErrorCode.BAD_REQUEST, message)
        adapter = runnable_channel_adapter(normalized, dict(saved.get("config") or {}) if saved else {})
        if adapter is None:
            message = f"Channel {normalized} is not available"
            self._channel_failure_audit(chatflow_id, normalized, message)
            raise BizError(ErrorCode.BAD_REQUEST, message)
        try:
            runtime_input = adapter.to_runtime_input(
                ChannelInboundRequest(
                    message=request.message,
                    conversation_id=request.conversation_id,
                    user_id=request.user_id,
                    channel_id=request.channel_id,
                    files=[dict(item) for item in request.files],
                    metadata=dict(request.metadata),
                )
            )
        except ValueError as exc:
            self._channel_failure_audit(chatflow_id, normalized, str(exc))
            raise BizError(ErrorCode.BAD_REQUEST, str(exc)) from exc
        run = self.execute(chatflow_id, WorkflowRunRequest(input=runtime_input))
        return {
            "channelId": normalized,
            "runtimeInput": runtime_input,
            "run": run,
            "deliveries": self._channel_deliveries(run),
        }

    def publish(self, workflow_id: int) -> dict[str, Any]:
        self._ensure_publish_repo(workflow_id)
        assert self._publish_repository is not None
        detail = self.get(workflow_id)
        snapshot = _json_safe({
            "workflow": {
                "id": detail["id"],
                "name": detail["name"],
                "description": detail["description"],
                "flowType": detail["flowType"],
                "status": detail["status"],
            },
            "nodes": self._repository.list_nodes(workflow_id),
            "edges": self._repository.list_edges(workflow_id),
        })
        validation = _publish_validation(snapshot)
        readiness_errors = self._publish_readiness_errors(workflow_id, snapshot)
        if readiness_errors:
            validation = {"valid": False, "errors": [*validation["errors"], *readiness_errors]}
        if not validation["valid"]:
            raise BizError(ErrorCode.BAD_REQUEST, validation["errors"][0])
        version = self._publish_repository.next_version(workflow_id, self._flow_type)
        row = self._publish_repository.create_version(
            workflow_id=workflow_id,
            flow_type=self._flow_type,
            version=version,
            snapshot=snapshot,
            validation=validation,
        )
        self._repository.update(workflow_id, {"status": "PUBLISHED"}, None, None, self._flow_type)
        response = self._version_response(row)
        self._audit(
            f"{self._flow_type}_PUBLISH",
            self._flow_type,
            workflow_id,
            metadata={"versionId": response["id"], "version": response["version"]},
        )
        return response

    def list_versions(self, workflow_id: int) -> dict[str, Any]:
        self._ensure_publish_repo(workflow_id)
        assert self._publish_repository is not None
        rows = self._publish_repository.list_versions(workflow_id, self._flow_type)
        return {"list": [self._version_response(row) for row in rows], "total": len(rows)}

    def rollback_version(self, workflow_id: int, version_id: int) -> dict[str, Any]:
        self._ensure_publish_repo(workflow_id)
        assert self._publish_repository is not None
        row = self._publish_repository.activate_version(workflow_id, self._flow_type, version_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Published version not found")
        response = self._version_response(row)
        self._audit(
            f"{self._flow_type}_ROLLBACK",
            self._flow_type,
            workflow_id,
            metadata={"versionId": response["id"], "version": response["version"]},
        )
        return response

    def execute_published(self, workflow_id: int, request: WorkflowRunRequest) -> dict[str, Any]:
        self._ensure_publish_repo(workflow_id)
        assert self._publish_repository is not None
        published_version = self._published_version_for_run(workflow_id, request.version_id)
        if published_version is None:
            raise BizError(ErrorCode.BAD_REQUEST, "No active published version")
        snapshot = published_version.get("snapshot") if isinstance(published_version.get("snapshot"), dict) else {}
        snapshot_repository = _SnapshotWorkflowRepository(
            self._repository,
            snapshot,
            publish_repository=self._publish_repository,
        )
        input_data = dict(request.input)
        if self._flow_type == "CHATFLOW":
            input_data = self._chatflow_runtime_input(workflow_id, input_data)
        try:
            result = WorkflowExecutionEngine(
                snapshot_repository,
                knowledge_facade=self._knowledge_facade_for(workflow_id),
                llm_completer=self._llm_completer(workflow_id),
                mcp_tool_executor=self._mcp_tool_executor,
                api_tool_executor=self._api_tool_executor,
                agent_invoker=self._agent_invoker_for(workflow_id),
                flow_type=self._flow_type,
                handoff_service=self._handoff_service,
            ).run(workflow_id, input_data)
        except WorkflowExecutionError as exc:
            raise BizError(ErrorCode.BAD_REQUEST, str(exc)) from exc
        data = WorkflowRunResponse(runId=result.run_id, status=result.status, output=result.output).model_dump(by_alias=True)
        if self._flow_type == "CHATFLOW" and self._chatflow_state_repository is not None:
            data.update(self._record_chatflow_state(workflow_id, input_data, result))
        data.update(self._debug_url_fields(workflow_id, result.run_id))
        data["versionId"] = int(published_version["id"])
        data["version"] = int(published_version["version"])
        self._audit(
            f"{self._flow_type}_RUN",
            f"{self._flow_type}_RUN",
            result.run_id,
            metadata={
                "workflowId": workflow_id,
                "status": result.status,
                "versionId": int(published_version["id"]),
                "version": int(published_version["version"]),
            },
        )
        return data

    def _published_version_for_run(self, workflow_id: int, version_id: int | None) -> dict[str, Any] | None:
        assert self._publish_repository is not None
        if version_id is None:
            return self._publish_repository.active_version(workflow_id, self._flow_type)
        row = self._publish_repository.get_version(workflow_id, self._flow_type, version_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Published version not found")
        return row

    def _publish_readiness_errors(self, workflow_id: int, snapshot: Mapping[str, Any]) -> list[str]:
        nodes = snapshot.get("nodes") if isinstance(snapshot.get("nodes"), list) else []
        errors: list[str] = []
        for node in nodes:
            if not isinstance(node, Mapping):
                continue
            node_key = str(node.get("node_key") or node.get("nodeKey") or "").strip()
            node_type = str(node.get("type") or "").upper()
            config = node.get("config") if isinstance(node.get("config"), Mapping) else {}
            if node_type == "EXECUTE_WORKFLOW":
                errors.extend(self._execute_workflow_readiness_errors(workflow_id, node_key, config))
            elif node_type == "LLM":
                errors.extend(self._llm_model_readiness_errors(node_key, config))
            elif node_type == "AGENT_CALL":
                errors.extend(self._agent_readiness_errors(node_key, config))
        return errors

    def _execute_workflow_readiness_errors(
        self,
        workflow_id: int,
        node_key: str,
        config: Mapping[str, Any],
    ) -> list[str]:
        target_id = _optional_positive_int(config.get("targetWorkflowId") or config.get("target_workflow_id") or config.get("workflowId"))
        if target_id is None:
            return []
        if target_id == workflow_id:
            return [f"{node_key} target workflow cannot be recursive"]
        target = self._repository.get(target_id, "WORKFLOW")
        if target is None:
            return [f"{node_key} target workflow not found"]
        if str(target.get("flow_type") or "WORKFLOW").upper() != "WORKFLOW":
            return [f"{node_key} target must be a Workflow"]
        if self._publish_repository is None:
            return [f"{node_key} target workflow published version cannot be verified"]
        if self._publish_repository.active_version(target_id, "WORKFLOW") is None:
            return [f"{node_key} target workflow must have an active published version"]
        return []

    def _llm_model_readiness_errors(self, node_key: str, config: Mapping[str, Any]) -> list[str]:
        if self._model_facade is None:
            return []
        raw_model_config_id = config.get("modelConfigId") or config.get("model_config_id")
        model_config_id = _optional_positive_int(raw_model_config_id)
        if raw_model_config_id not in (None, "") and model_config_id is not None:
            try:
                self._model_facade.get_enabled_model_config(model_config_id)
            except BizError:
                return [f"{node_key} modelConfigId is not ready"]
        model_id = str(config.get("modelId") or config.get("model_id") or "").strip()
        if model_id and self._model_facade.find_enabled_model_config_by_model_id(model_id) is None:
            return [f"{node_key} modelId is not ready: {model_id}"]
        return []

    def _agent_readiness_errors(self, node_key: str, config: Mapping[str, Any]) -> list[str]:
        if self._agent_repository is None:
            return []
        target_agent_id = _optional_positive_int(config.get("targetAgentId") or config.get("target_agent_id") or config.get("agentId"))
        if target_agent_id is None:
            return []
        agent = self._agent_repository.get(target_agent_id)
        if agent is None:
            return [f"{node_key} target agent not found"]
        if not bool(agent.get("enabled")):
            return [f"{node_key} target agent is disabled"]
        if agent.get("workflow_id") is not None:
            return [f"{node_key} workflow-bound agent is not allowed"]
        return []

    def _debug_url_fields(self, workflow_id: int, run_id: int) -> dict[str, str]:
        prefix = "chatflows" if self._flow_type == "CHATFLOW" else "workflows"
        url = f"/{prefix}/{workflow_id}/canvas?runId={run_id}&debug=1"
        return {"debugUrl": url, "debug_url": url}

    def _chatflow_runtime_input(self, chatflow_id: int, input_data: dict[str, Any]) -> dict[str, Any]:
        input_data = _normalize_chatflow_runtime_context(input_data)
        if self._chatflow_state_repository is None:
            return input_data
        if input_data.get("history") or input_data.get("conversationHistory"):
            return input_data
        nodes = self._repository.list_nodes(chatflow_id)
        if not _needs_persisted_history(nodes):
            return input_data
        history_limit = _chatflow_history_retention_limit(nodes, input_data)
        if history_limit <= 0:
            return input_data
        session_id = _chatflow_explicit_session_id(input_data)
        if not session_id:
            return input_data
        history = self._chatflow_state_repository.recent_message_history(chatflow_id, session_id, limit=history_limit)
        if not history:
            return input_data
        enriched = dict(input_data)
        enriched["history"] = history
        return enriched

    def _ensure_chatflow_and_channel_repo(self, chatflow_id: int) -> None:
        if self._flow_type != "CHATFLOW":
            raise BizError(ErrorCode.BAD_REQUEST, "Chatflow channels are only available for Chatflow")
        if self._repository.get(chatflow_id, self._flow_type) is None:
            raise BizError(ErrorCode.NOT_FOUND, "Chatflow not found")
        if self._channel_repository is None:
            raise BizError(ErrorCode.BAD_REQUEST, "Chatflow channel repository is not configured")

    def _ensure_publish_repo(self, workflow_id: int) -> None:
        if self._repository.get(workflow_id, self._flow_type) is None:
            raise BizError(ErrorCode.NOT_FOUND, "Workflow not found")
        if self._publish_repository is None:
            raise BizError(ErrorCode.BAD_REQUEST, "Workflow publish repository is not configured")

    def _channel_response(self, shell: Any, saved: Mapping[str, Any] | None) -> dict[str, Any]:
        config = dict(saved.get("config") or {}) if saved else {}
        enabled = bool(saved.get("enabled")) if saved else shell.runnable
        return {
            "channelId": shell.channel_id,
            "displayName": str(saved.get("display_name") or shell.display_name) if saved else shell.display_name,
            "enabled": enabled and shell.runnable,
            "runnable": bool(shell.runnable),
            "config": config,
            "configSchema": dict(getattr(shell, "config_schema", {}) or {"type": "object", "properties": {}, "required": []}),
            "deliveryCapabilities": dict(
                getattr(shell, "delivery_capabilities", {})
                or {"sync": False, "streaming": False, "files": False, "cards": False}
            ),
            "normalizedInputFields": list(getattr(shell, "normalized_input_fields", ()) or ()),
            "unavailableReason": "" if shell.runnable else shell.unavailable_reason,
        }

    def _channel_deliveries(self, run: Mapping[str, Any]) -> list[dict[str, Any]]:
        output = run.get("output") if isinstance(run.get("output"), Mapping) else {}
        message = str(output.get("output") or output.get("answer") or output.get("final") or "")
        if not message and output:
            message = str(output)
        return [{"type": "message", "status": "delivered", "content": message}]

    def _channel_failure_audit(self, chatflow_id: int, channel_id: str, error: str) -> None:
        self._audit(
            "CHANNEL_DELIVERY_FAILED",
            "CHATFLOW_CHANNEL",
            f"{chatflow_id}:{channel_id}",
            status="failed",
            metadata={"deliveryStatus": "failed", "channelId": channel_id, "error": error},
        )

    def _audit(
        self,
        action: str,
        resource_type: str,
        resource_id: str | int,
        status: str = "succeeded",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if self._audit_repository is None:
            return
        self._audit_repository.record(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            metadata=metadata or {},
            request_context=self._request_context,
        )

    def _version_response(self, row: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "workflowId": int(row["workflow_id"]),
            "flowType": row["flow_type"],
            "version": int(row["version"]),
            "active": bool(row["active"]),
            "validation": row.get("validation") or {},
            "snapshot": row.get("snapshot") or {},
            "createdAt": format_datetime(row["created_at"]),
            "updatedAt": format_datetime(row["updated_at"]),
        }

    def _record_chatflow_state(
        self,
        chatflow_id: int,
        input_data: dict[str, Any],
        result: Any,
    ) -> dict[str, Any]:
        assert self._chatflow_state_repository is not None
        session_id = _chatflow_session_id(chatflow_id, result.run_id, input_data)
        conversation_id = str(input_data.get("sys.conversation_id") or input_data.get("conversationId") or session_id)
        user_id = str(input_data.get("sys.user_id") or input_data.get("userId") or "")
        channel = str(input_data.get("sys.channel") or input_data.get("channel") or "web")
        channel_id = str(input_data.get("sys.channel_id") or input_data.get("channelId") or "")
        session_status = _chatflow_session_status(result.status, result.output)
        variable_scopes = _result_variable_scopes(result)
        node_runs = self._repository.list_node_runs(result.run_id)
        node_outputs = {
            str(node_run["node_key"]): node_run.get("outputs") or {}
            for node_run in node_runs
        }
        session_variables = {**variable_scopes, "node_outputs": node_outputs}
        self._chatflow_state_repository.create_session(
            session_id=session_id,
            chatflow_id=chatflow_id,
            conversation_id=conversation_id,
            user_id=user_id,
            channel=channel,
            channel_id=channel_id,
            status=session_status,
            current_run_id=result.run_id,
            variables=session_variables,
        )

        formatted_events: list[dict[str, Any]] = []
        for event in _message_events_from_node_runs(node_runs):
            event_type = "handoff_requested" if str(event.get("rawType") or "") == "handoff_requested" else "message"
            row = self._chatflow_state_repository.append_event(
                session_id=session_id,
                chatflow_id=chatflow_id,
                run_id=result.run_id,
                event_type=event_type,
                node_key=str(event.get("nodeKey") or ""),
                payload=event,
            )
            formatted_events.append(_format_chatflow_event(row))

        checkpoint_id: int | None = None
        if result.status == "INTERRUPTED":
            interrupt_payload = dict(result.output.get("interrupt") or {})
            pending_node_key = str(interrupt_payload.get("nodeKey") or "")
            checkpoint = self._chatflow_state_repository.create_checkpoint(
                session_id=session_id,
                chatflow_id=chatflow_id,
                run_id=result.run_id,
                pending_node_key=pending_node_key,
                execution_context={"input": input_data},
                node_outputs=node_outputs,
                variable_scopes=variable_scopes,
                resume_schema=interrupt_payload,
            )
            checkpoint_id = int(checkpoint["id"])
            event_row = self._chatflow_state_repository.append_event(
                session_id=session_id,
                chatflow_id=chatflow_id,
                run_id=result.run_id,
                event_type="interrupt",
                node_key=pending_node_key,
                payload=interrupt_payload,
                checkpoint_id=checkpoint_id,
            )
            self._chatflow_state_repository.link_checkpoint_event(checkpoint_id, int(event_row["id"]))
            formatted_events.append(_format_chatflow_event(event_row))
        elif result.status == "SUCCEEDED":
            row = self._chatflow_state_repository.append_event(
                session_id=session_id,
                chatflow_id=chatflow_id,
                run_id=result.run_id,
                event_type="done",
                payload={"output": result.output},
            )
            formatted_events.append(_format_chatflow_event(row))
        else:
            row = self._chatflow_state_repository.append_event(
                session_id=session_id,
                chatflow_id=chatflow_id,
                run_id=result.run_id,
                event_type="error",
                payload={"output": result.output},
            )
            formatted_events.append(_format_chatflow_event(row))

        return {
            "sessionId": session_id,
            "sessionStatus": session_status,
            "checkpointId": checkpoint_id,
            "events": formatted_events,
            "streamEvents": _stream_events_from_node_runs(node_runs),
        }

    def get_session_state(self, chatflow_id: int, session_id: str) -> dict[str, Any]:
        if self._chatflow_state_repository is None:
            raise BizError(ErrorCode.BAD_REQUEST, "Chatflow session state is not configured")
        session = self._chatflow_state_repository.get_session(chatflow_id, session_id)
        if session is None:
            raise BizError(ErrorCode.NOT_FOUND, "Chatflow session not found")
        waiting_event = (
            self._chatflow_state_repository.latest_waiting_event(chatflow_id, session_id)
            if str(session["status"]) == "waiting"
            else None
        )
        checkpoint = (
            self._chatflow_state_repository.latest_checkpoint(chatflow_id, session_id)
            if str(session["status"]) == "waiting"
            else None
        )
        return {
            "sessionId": session["session_id"],
            "chatflowId": int(session["chatflow_id"]),
            "conversationId": session["conversation_id"],
            "userId": session["user_id"],
            "channel": session["channel"],
            "channelId": session["channel_id"],
            "status": session["status"],
            "currentRunId": int(session["current_run_id"] or 0),
            "variables": session["variables"] or {},
            "expiresAt": format_datetime(session["expires_at"]) if session.get("expires_at") else None,
            "waitingEvent": _format_chatflow_event(waiting_event) if waiting_event else None,
            "checkpoint": _format_chatflow_checkpoint(checkpoint) if checkpoint else None,
        }

    def list_run_events(self, chatflow_id: int, run_id: int) -> dict[str, Any]:
        if self._chatflow_state_repository is None:
            raise BizError(ErrorCode.BAD_REQUEST, "Chatflow session state is not configured")
        events = self._chatflow_state_repository.list_events(chatflow_id, run_id)
        return {"list": [_format_chatflow_event(event) for event in events], "total": len(events)}

    def list_session_events(
        self,
        chatflow_id: int,
        session_id: str,
        after_event_id: int = 0,
    ) -> dict[str, Any]:
        if self._chatflow_state_repository is None:
            raise BizError(ErrorCode.BAD_REQUEST, "Chatflow session state is not configured")
        if self._chatflow_state_repository.get_session(chatflow_id, session_id) is None:
            raise BizError(ErrorCode.NOT_FOUND, "Chatflow session not found")
        events = self._chatflow_state_repository.list_session_events(chatflow_id, session_id, after_event_id)
        return {"list": [_format_chatflow_event(event) for event in events], "total": len(events)}

    def resume_run(self, chatflow_id: int, run_id: int, request: WorkflowResumeRequest) -> dict[str, Any]:
        if self._flow_type != "CHATFLOW" or self._chatflow_state_repository is None:
            raise BizError(ErrorCode.BAD_REQUEST, "Chatflow resume is not configured")
        if self._repository.get(chatflow_id, self._flow_type) is None:
            raise BizError(ErrorCode.NOT_FOUND, "Chatflow not found")
        if request.idempotency_key:
            replay_event = self._chatflow_state_repository.find_resume_event_by_idempotency_key(
                chatflow_id,
                run_id,
                request.idempotency_key,
            )
            if replay_event is not None:
                return self._replay_resume_result(chatflow_id, run_id, replay_event)
        checkpoint = self._chatflow_state_repository.get_waiting_checkpoint(chatflow_id, run_id, request.event_id)
        if checkpoint is None:
            raise BizError(ErrorCode.NOT_FOUND, "Chatflow checkpoint not found")
        if _is_expired(checkpoint.get("expires_at")):
            raise BizError(ErrorCode.BAD_REQUEST, "Chatflow checkpoint expired")
        session_id = str(checkpoint["session_id"])
        session = self._chatflow_state_repository.get_session(chatflow_id, session_id)
        if session is not None and _is_expired(session.get("expires_at")):
            self._chatflow_state_repository.update_session_status(
                chatflow_id=chatflow_id,
                session_id=session_id,
                status="expired",
                current_run_id=run_id,
            )
            raise BizError(ErrorCode.BAD_REQUEST, "Chatflow session expired")
        pending_node_key = str(checkpoint["pending_node_key"])
        resume_data = _merged_resume_data(dict(request.resume_data), checkpoint.get("resume_schema"))
        execution_context = checkpoint.get("execution_context") if isinstance(checkpoint.get("execution_context"), dict) else {}
        input_data = dict(execution_context.get("input") or {})
        input_data["resume"] = {pending_node_key: resume_data}
        node_outputs = checkpoint.get("node_outputs") if isinstance(checkpoint.get("node_outputs"), dict) else {}
        variable_scopes = checkpoint.get("variable_scopes") if isinstance(checkpoint.get("variable_scopes"), dict) else {}

        resume_event = self._chatflow_state_repository.append_event(
            session_id=session_id,
            chatflow_id=chatflow_id,
            run_id=run_id,
            event_type="resume",
            node_key=pending_node_key,
            payload={"resumeData": resume_data, "idempotencyKey": request.idempotency_key or ""},
            checkpoint_id=int(checkpoint["id"]),
        )
        try:
            result = WorkflowExecutionEngine(
                self._repository,
                knowledge_facade=self._knowledge_facade_for(chatflow_id),
                llm_completer=self._llm_completer(chatflow_id),
                mcp_tool_executor=self._mcp_tool_executor,
                api_tool_executor=self._api_tool_executor,
                agent_invoker=self._agent_invoker_for(chatflow_id),
                flow_type=self._flow_type,
                handoff_service=self._handoff_service,
            ).resume(chatflow_id, run_id, pending_node_key, input_data, node_outputs, variable_scopes)
        except WorkflowExecutionError as exc:
            raise BizError(ErrorCode.BAD_REQUEST, str(exc)) from exc

        self._chatflow_state_repository.mark_checkpoint_completed(int(checkpoint["id"]))
        session_status = _chatflow_session_status(result.status, result.output)
        self._chatflow_state_repository.update_session_status(
            chatflow_id=chatflow_id,
            session_id=session_id,
            status=session_status,
            current_run_id=run_id,
            variables=result.variable_scopes,
        )
        done_event = self._chatflow_state_repository.append_event(
            session_id=session_id,
            chatflow_id=chatflow_id,
            run_id=run_id,
            event_type="done" if result.status == "SUCCEEDED" else "interrupt",
            payload={"output": result.output},
        )
        node_runs = self._repository.list_node_runs(run_id)
        return {
            "runId": result.run_id,
            "status": result.status,
            "output": result.output,
            "sessionId": session_id,
            "sessionStatus": session_status,
            "checkpointId": int(checkpoint["id"]),
            "events": [_format_chatflow_event(resume_event), _format_chatflow_event(done_event)],
            "streamEvents": _stream_events_from_node_runs(node_runs),
        }

    def _replay_resume_result(self, chatflow_id: int, run_id: int, resume_event: dict[str, Any]) -> dict[str, Any]:
        assert self._chatflow_state_repository is not None
        events = self._chatflow_state_repository.list_events(chatflow_id, run_id)
        resume_sequence = int(resume_event["sequence"])
        terminal_event = next(
            (
                event
                for event in reversed(events)
                if int(event["sequence"]) >= resume_sequence
                and str(event["event_type"]) in {"done", "interrupt", "error"}
            ),
            None,
        )
        status_by_event = {"done": "SUCCEEDED", "interrupt": "INTERRUPTED", "error": "FAILED"}
        status = status_by_event.get(str(terminal_event["event_type"]) if terminal_event else "", "SUCCEEDED")
        payload = terminal_event.get("payload") if terminal_event else {}
        output = payload.get("output") if isinstance(payload, Mapping) and isinstance(payload.get("output"), dict) else {}
        session_id = str(resume_event["session_id"])
        session = self._chatflow_state_repository.get_session(chatflow_id, session_id)
        return {
            "runId": run_id,
            "status": status,
            "output": output,
            "sessionId": session_id,
            "sessionStatus": str(session["status"]) if session else _chatflow_session_status(status),
            "checkpointId": int(resume_event["checkpoint_id"] or 0),
            "events": [_format_chatflow_event(event) for event in events],
        }

    def _knowledge_facade_for(self, workflow_id: int) -> KnowledgeFacade | None:
        nodes = self._repository.list_nodes(workflow_id)
        if not self._needs_knowledge_facade(nodes):
            return None
        if self._knowledge_facade is None:
            raise BizError(ErrorCode.BAD_REQUEST, "Workflow knowledge facade is not configured")
        return self._knowledge_facade

    def _agent_invoker_for(self, workflow_id: int) -> _ChatServiceAgentInvocationFacade | None:
        nodes = self._repository.list_nodes(workflow_id)
        if not any(node["type"] == "AGENT_CALL" for node in nodes):
            return None
        if self._agent_repository is None or self._model_facade is None:
            raise BizError(ErrorCode.BAD_REQUEST, "AGENT_CALL runtime is not configured")
        chat_service = ChatService(
            ChatRepository(self._repository.session),
            knowledge_facade=self._knowledge_facade,
            mcp_facade=self._mcp_tool_executor,  # type: ignore[arg-type]
            model_facade=self._model_facade,
            request_builder=self._request_builder,
            parser=self._parser,
            llm_client_factory=self._llm_client_factory,
        )
        return _ChatServiceAgentInvocationFacade(
            agent_repository=self._agent_repository,
            chat_service=chat_service,
        )

    def _needs_knowledge_facade(self, nodes: list[dict[str, Any]]) -> bool:
        if any(node["type"] == "KNOWLEDGE" for node in nodes):
            return True
        return any(
            node["type"] == "LLM" and _has_enabled_knowledge_resource(node.get("config"))
            for node in nodes
        )

    def _has_start_node(self, workflow_id: int) -> bool:
        return any(node["type"] == "START" for node in self._repository.list_nodes(workflow_id))

    def _llm_completer(self, workflow_id: int) -> WorkflowLlmCompleter | None:
        nodes = self._repository.list_nodes(workflow_id)
        if not any(
            node["type"] == "LLM" or _is_llm_intent_node(node) or _is_llm_information_collection_node(node)
            for node in nodes
        ):
            return None
        node_config_completer = self._node_config_llm_completer(workflow_id)
        if node_config_completer is not None:
            return node_config_completer
        if self._agent_repository is None or self._model_facade is None:
            return None
        agent = self._preferred_live_llm_agent()
        if agent is None:
            raise BizError(ErrorCode.BAD_REQUEST, "Workflow LLM agent is not configured")
        model_config = self._model_facade.get_enabled_model_config(int(agent["model_config_id"]))
        if model_config.provider_base_url.startswith("mock://"):
            raise BizError(ErrorCode.BAD_REQUEST, "Workflow LLM agent must use a real provider")
        return _AgentBackedWorkflowLlmCompleter(
            agent=agent,
            model_config=model_config,
            model_facade=self._model_facade,
            request_builder=self._request_builder,
            parser=self._parser,
            llm_client_factory=self._llm_client_factory,
        )

    def runtime_v2_llm_completer(self, workflow_id: int) -> WorkflowLlmCompleter | None:
        node_config_completer = self._node_config_llm_completer(workflow_id)
        if node_config_completer is not None:
            return node_config_completer
        try:
            completer = self._llm_completer(workflow_id)
            if completer is not None:
                return completer
        except BizError as exc:
            if exc.message in {
                "Workflow LLM agent is not configured",
                "Workflow LLM agent must use a real provider",
            }:
                pass
            else:
                raise
        return None

    def _node_config_llm_completer(self, workflow_id: int) -> WorkflowLlmCompleter | None:
        nodes = self._repository.list_nodes(workflow_id)
        if not any(node["type"] == "LLM" and _has_node_model_config(node.get("config")) for node in nodes):
            return None
        if self._model_facade is None:
            return None
        return _NodeConfigWorkflowLlmCompleter(
            model_facade=self._model_facade,
            request_builder=self._request_builder,
            parser=self._parser,
            llm_client_factory=self._llm_client_factory,
        )

    def runtime_v2_agent_invoker(self, workflow_id: int) -> _ChatServiceAgentInvocationFacade | None:
        return self._agent_invoker_for(workflow_id)

    def runtime_v2_mcp_tool_executor(self) -> McpToolExecutor | None:
        return self._mcp_tool_executor

    def runtime_v2_api_tool_executor(self) -> ApiToolExecutor | None:
        return self._api_tool_executor

    def _preferred_live_llm_agent(self) -> dict[str, Any] | None:
        if self._agent_repository is None:
            return None
        preferred_name = (self._preferred_llm_agent_name or "").strip()
        if preferred_name and hasattr(self._agent_repository, "find_live_llm_agent_by_name"):
            agent = self._agent_repository.find_live_llm_agent_by_name(preferred_name)
            if agent is not None:
                return agent
        return self._agent_repository.find_default_live_llm_agent()

    def _response(self, row: dict[str, Any]) -> WorkflowResponse:
        return WorkflowResponse(
            id=int(row["id"]),
            name=row["name"],
            description=row["description"] or "",
            flowType=row.get("flow_type") or "WORKFLOW",
            status=row["status"],
            createdAt=format_datetime(row["created_at"]),
            updatedAt=format_datetime(row["updated_at"]),
        )

    def _detail_response(self, row: dict[str, Any]) -> WorkflowDetailResponse:
        workflow_id = int(row["id"])
        return WorkflowDetailResponse(
            **self._response(row).model_dump(by_alias=True),
            nodes=[
                WorkflowNodeResponse(
                    nodeKey=node["node_key"],
                    type=node["type"],
                    name=node["name"] or "",
                    config=node["config"] or {},
                )
                for node in self._repository.list_nodes(workflow_id)
            ],
            edges=[
                WorkflowEdgeResponse(
                    sourceNodeKey=edge["source_node_key"],
                    targetNodeKey=edge["target_node_key"],
                    condition=edge["condition_expr"],
                )
                for edge in self._repository.list_edges(workflow_id)
            ],
        )


class _ChatServiceAgentInvocationFacade:
    def __init__(
        self,
        agent_repository: AgentRepository,
        chat_service: ChatService,
    ) -> None:
        self._agent_repository = agent_repository
        self._chat_service = chat_service

    def invoke_agent(
        self,
        *,
        agent_id: int,
        message: str,
        variables: dict[str, Any],
        history: list[dict[str, Any]],
        timeout_ms: int,
        parent_agent_ids: tuple[int, ...],
        max_depth: int,
    ) -> AgentInvocationResult:
        if agent_id in parent_agent_ids:
            raise WorkflowExecutionError("AGENT_CALL recursive target is not allowed")
        if len(parent_agent_ids) + 1 > max_depth:
            raise WorkflowExecutionError("AGENT_CALL maxDepth exceeded")

        agent = self._agent_repository.get(agent_id)
        if agent is None:
            raise WorkflowExecutionError("AGENT_CALL target agent not found")
        if not bool(agent.get("enabled")):
            raise WorkflowExecutionError("AGENT_CALL target agent is disabled")
        if agent.get("workflow_id") is not None:
            raise WorkflowExecutionError("AGENT_CALL workflow-bound agent is not allowed")

        session = self._chat_service.create_session(ChatSessionCreateRequest(agentId=agent_id))
        session_id = int(session["id"])
        started_at = datetime.now()
        turn = self._chat_service.send_message(
            session_id,
            ChatMessageCreateRequest(content=message, stream=False, variables=variables),
        )
        assistant = turn["assistantMessage"]
        latency_ms = int((datetime.now() - started_at).total_seconds() * 1000)
        return AgentInvocationResult(
            session_id=session_id,
            content=str(assistant.get("content") or ""),
            status="SUCCEEDED",
            latency_ms=latency_ms,
            tool_calls=assistant.get("toolCalls") if isinstance(assistant.get("toolCalls"), list) else [],
        )


class _NodeConfigWorkflowLlmCompleter:
    def __init__(
        self,
        model_facade: ProviderModelFacade,
        request_builder: OpenAIChatRequestBuilder,
        parser: OpenAIAdapterParser,
        llm_client_factory: LlmClientFactory,
    ) -> None:
        self._model_facade = model_facade
        self._request_builder = request_builder
        self._parser = parser
        self._llm_client_factory = llm_client_factory
        self._last_call_debug: dict[str, Any] = {}

    def complete_prompt(self, prompt: str, options: dict[str, Any] | None = None) -> str:
        options = options or {}
        model_config = self._active_model_config(options)
        payload = self._request_builder.build(
            model=str(options.get("model") or model_config.model_id),
            messages=self._messages(prompt, str(options.get("systemPrompt") or "")),
            temperature=_optional_float(options.get("temperature"), None),
            max_tokens=_optional_int(options.get("maxTokens") or options.get("max_tokens"), None),
            extra_params=self._extra_params(options, model_config),
        )
        started_at = perf_counter()
        response, fallback_debug = self._complete_with_fallback(payload, model_config)
        elapsed_ms = int((perf_counter() - started_at) * 1000)
        result = self._parser.parse_chat_response(response)
        self._last_call_debug = {
            "model": str(response.get("model") or fallback_debug.get("effectiveModel") or payload.get("model") or model_config.model_id),
            "elapsedMs": elapsed_ms,
            "input": _redact_llm_payload(payload),
            "output": {
                "content": result.content,
                "finishReason": result.finish_reason,
            },
            "usage": _usage_from_llm_response(response, payload, result.content),
        }
        if fallback_debug:
            self._last_call_debug.update(
                {
                    "requestModel": fallback_debug["requestModel"],
                    "fallbackModel": fallback_debug["fallbackModel"],
                    "fallbackUsed": True,
                    "fallbackReason": fallback_debug["fallbackReason"],
                    "fallback": fallback_debug["fallback"],
                }
            )
        return result.content

    def supports_tool_calls(self) -> bool:
        return True

    def complete_prompt_with_tools(
        self,
        prompt: str,
        options: dict[str, Any] | None,
        tools: list[ToolDefinition],
        tool_ids: list[int],
        mcp_facade: McpToolExecutor,
    ) -> tuple[str, list[dict[str, Any]]]:
        options = options or {}
        model_config = self._active_model_config(options)
        if str(model_config.provider_type or "").upper() not in {"OPENAI", "OPENAI_COMPATIBLE"}:
            raise WorkflowExecutionError("Selected Workflow LLM provider/model does not support tool calls")
        messages = self._messages(prompt, str(options.get("systemPrompt") or ""))
        result = ChatOrchestrator(
            request_builder=self._request_builder,
            parser=self._parser,
        ).run(
            model=str(options.get("model") or model_config.model_id),
            messages=messages,
            tools=tools,
            tool_ids=tool_ids,
            mcp_facade=mcp_facade,
            llm_client=self._llm_client(model_config),
            temperature=_optional_float(options.get("temperature"), None),
            max_tokens=_optional_int(options.get("maxTokens") or options.get("max_tokens"), None),
            extra_params=self._extra_params(options, model_config),
        )
        prompt_text = "\n".join(message.content for message in messages)
        self._last_call_debug = {
            "model": str(options.get("model") or model_config.model_id),
            "elapsedMs": 0,
            "input": {"messages": [{"role": "user", "content": prompt_text}], "tools": [tool.name for tool in tools]},
            "output": {"content": result.final_content},
            "usage": _estimated_usage(prompt_text, result.final_content),
        }
        return result.final_content, [
            _llm_tool_call_evidence(item)
            for item in result.tool_results
        ]

    def _messages(self, prompt: str, node_system_prompt: str = "") -> list[ChatRequestMessage]:
        messages: list[ChatRequestMessage] = []
        if node_system_prompt:
            messages.append(ChatRequestMessage(role="system", content=node_system_prompt))
        messages.append(ChatRequestMessage(role="user", content=prompt))
        return messages

    def _active_model_config(self, options: Mapping[str, Any]) -> ModelConfigDto:
        raw_model_config_id = options.get("modelConfigId") or options.get("model_config_id")
        if raw_model_config_id not in (None, ""):
            try:
                return self._model_facade.get_enabled_model_config(int(raw_model_config_id))
            except (TypeError, ValueError) as exc:
                raise WorkflowExecutionError("LLM node modelConfigId is invalid") from exc
        raw_model = str(options.get("model") or "").strip()
        if raw_model and hasattr(self._model_facade, "find_enabled_model_config_by_model_id"):
            matched = self._model_facade.find_enabled_model_config_by_model_id(raw_model)  # type: ignore[attr-defined]
            if matched is not None:
                return matched
        raise WorkflowExecutionError("LLM node modelConfigId is required")

    def _extra_params(self, options: dict[str, Any], model_config: ModelConfigDto) -> dict[str, Any]:
        extra_params = dict(model_config.extra_params or {})
        mapped = {
            "top_p": options.get("topP") or options.get("top_p"),
            "frequency_penalty": options.get("frequencyPenalty") or options.get("frequency_penalty"),
            "presence_penalty": options.get("presencePenalty") or options.get("presence_penalty"),
            "seed": options.get("seed"),
        }
        for key, value in mapped.items():
            if value is not None and value != "":
                extra_params[key] = _optional_float(value, value) if key != "seed" else _optional_int(value, value)
        response_format = options.get("responseFormat") or options.get("response_format")
        if isinstance(response_format, dict):
            extra_params["response_format"] = response_format
        elif str(response_format or "").upper() == "JSON":
            extra_params["response_format"] = {"type": "json_object"}
        stop = options.get("stopSequences") or options.get("stop")
        if isinstance(stop, str) and stop.strip():
            extra_params["stop"] = [item.strip() for item in stop.split("\n") if item.strip()]
        elif isinstance(stop, list) and stop:
            extra_params["stop"] = [str(item) for item in stop if str(item)]
        tool_choice = str(options.get("toolChoiceMode") or "").strip().lower()
        if tool_choice in {"auto", "required", "none"}:
            extra_params["tool_choice"] = tool_choice
        return extra_params

    def _llm_client(self, model_config: ModelConfigDto) -> Any:
        return self._llm_client_factory(
            ProviderChatConfig(
                provider_type=model_config.provider_type,
                base_url=model_config.provider_base_url,
                auth_config=model_config.provider_auth_config,
            )
        )

    def _complete_with_fallback(self, payload: dict[str, Any], model_config: ModelConfigDto) -> tuple[dict[str, Any], dict[str, Any]]:
        client = self._llm_client(model_config)
        request_model = str(payload.get("model") or model_config.model_id)
        try:
            return client.complete(payload), {}
        except Exception as exc:
            fallback_model = self._fallback_model(model_config)
            if not fallback_model or fallback_model == payload.get("model"):
                raise WorkflowExecutionError(f"LLM provider request failed: {_provider_request_error_message(exc)}") from exc
            primary_reason = _provider_request_error_message(exc)
            attempts = [{"model": request_model, "status": "failed", "reason": primary_reason}]
            fallback_payload = dict(payload)
            fallback_payload["model"] = fallback_model
            try:
                response = client.complete(fallback_payload)
            except Exception as fallback_exc:
                attempts.append(
                    {
                        "model": fallback_model,
                        "status": "failed",
                        "reason": _provider_request_error_message(fallback_exc),
                    }
                )
                raise WorkflowExecutionError(f"LLM provider request failed: {_provider_request_error_message(fallback_exc)}") from fallback_exc
            attempts.append({"model": fallback_model, "status": "succeeded"})
            return response, {
                "requestModel": request_model,
                "fallbackModel": fallback_model,
                "fallbackReason": primary_reason,
                "effectiveModel": fallback_model,
                "fallback": {"attempted": True, "attempts": attempts},
            }

    def _fallback_model(self, model_config: ModelConfigDto) -> str:
        extra_params = dict(model_config.extra_params or {})
        return str(extra_params.get("fallbackModel") or extra_params.get("fallback_model") or "").strip()

    def consume_last_call_debug(self) -> dict[str, Any]:
        debug = dict(self._last_call_debug)
        self._last_call_debug = {}
        return debug


class _AgentBackedWorkflowLlmCompleter:
    def __init__(
        self,
        agent: dict[str, Any],
        model_config: ModelConfigDto,
        model_facade: ProviderModelFacade | None,
        request_builder: OpenAIChatRequestBuilder,
        parser: OpenAIAdapterParser,
        llm_client_factory: LlmClientFactory,
    ) -> None:
        self._agent = agent
        self._model_config = model_config
        self._model_facade = model_facade
        self._request_builder = request_builder
        self._parser = parser
        self._llm_client_factory = llm_client_factory
        self._last_call_debug: dict[str, Any] = {}

    def complete_prompt(self, prompt: str, options: dict[str, Any] | None = None) -> str:
        options = options or {}
        model_config = self._active_model_config(options)
        payload = self._request_builder.build(
            model=str(options.get("model") or model_config.model_id),
            messages=self._messages(prompt, str(options.get("systemPrompt") or "")),
            temperature=_optional_float(options.get("temperature"), float(self._agent["temperature"])),
            max_tokens=_optional_int(options.get("maxTokens") or options.get("max_tokens"), int(self._agent["max_tokens"])),
            extra_params=self._extra_params(options, model_config),
        )
        started_at = perf_counter()
        response, fallback_debug = self._complete_with_fallback(payload, model_config)
        elapsed_ms = int((perf_counter() - started_at) * 1000)
        result = self._parser.parse_chat_response(response)
        self._last_call_debug = {
            "model": str(response.get("model") or fallback_debug.get("effectiveModel") or payload.get("model") or model_config.model_id),
            "elapsedMs": elapsed_ms,
            "input": _redact_llm_payload(payload),
            "output": {
                "content": result.content,
                "finishReason": result.finish_reason,
            },
            "usage": _usage_from_llm_response(response, payload, result.content),
        }
        if fallback_debug:
            self._last_call_debug.update(
                {
                    "requestModel": fallback_debug["requestModel"],
                    "fallbackModel": fallback_debug["fallbackModel"],
                    "fallbackUsed": True,
                    "fallbackReason": fallback_debug["fallbackReason"],
                    "fallback": fallback_debug["fallback"],
                }
            )
        return result.content

    def supports_tool_calls(self) -> bool:
        return str(self._model_config.provider_type or "").upper() == "OPENAI"

    def complete_prompt_with_tools(
        self,
        prompt: str,
        options: dict[str, Any] | None,
        tools: list[ToolDefinition],
        tool_ids: list[int],
        mcp_facade: McpToolExecutor,
    ) -> tuple[str, list[dict[str, Any]]]:
        if not self.supports_tool_calls():
            raise WorkflowExecutionError("Selected Workflow LLM provider/model does not support tool calls")
        options = options or {}
        model_config = self._active_model_config(options)
        result = ChatOrchestrator(
            request_builder=self._request_builder,
            parser=self._parser,
        ).run(
            model=str(options.get("model") or model_config.model_id),
            messages=self._messages(prompt, str(options.get("systemPrompt") or "")),
            tools=tools,
            tool_ids=tool_ids,
            mcp_facade=mcp_facade,
            llm_client=self._llm_client(model_config),
            temperature=_optional_float(options.get("temperature"), float(self._agent["temperature"])),
            max_tokens=_optional_int(options.get("maxTokens") or options.get("max_tokens"), int(self._agent["max_tokens"])),
            extra_params=self._extra_params(options, model_config),
        )
        prompt_text = "\n".join(message.content for message in self._messages(prompt, str(options.get("systemPrompt") or "")))
        self._last_call_debug = {
            "model": str(options.get("model") or model_config.model_id),
            "elapsedMs": 0,
            "input": {"messages": [{"role": "user", "content": prompt_text}], "tools": [tool.name for tool in tools]},
            "output": {"content": result.final_content},
            "usage": _estimated_usage(prompt_text, result.final_content),
        }
        return result.final_content, [
            _llm_tool_call_evidence(item)
            for item in result.tool_results
        ]

    def _messages(self, prompt: str, node_system_prompt: str = "") -> list[ChatRequestMessage]:
        messages: list[ChatRequestMessage] = []
        system_prompt = str(self._agent.get("system_prompt") or "")
        if system_prompt:
            messages.append(ChatRequestMessage(role="system", content=system_prompt))
        if node_system_prompt:
            messages.append(ChatRequestMessage(role="system", content=node_system_prompt))
        messages.append(ChatRequestMessage(role="user", content=prompt))
        return messages

    def _active_model_config(self, options: Mapping[str, Any]) -> ModelConfigDto:
        raw_model_config_id = options.get("modelConfigId") or options.get("model_config_id")
        if self._model_facade is None:
            return self._model_config
        if raw_model_config_id in (None, ""):
            raw_model = str(options.get("model") or "").strip()
            if raw_model and raw_model != self._model_config.model_id and hasattr(self._model_facade, "find_enabled_model_config_by_model_id"):
                matched = self._model_facade.find_enabled_model_config_by_model_id(raw_model)  # type: ignore[attr-defined]
                if matched is not None:
                    return matched
            return self._model_config
        try:
            model_config_id = int(raw_model_config_id)
        except (TypeError, ValueError) as exc:
            raise WorkflowExecutionError("LLM node modelConfigId is invalid") from exc
        if model_config_id == int(self._model_config.id):
            return self._model_config
        return self._model_facade.get_enabled_model_config(model_config_id)

    def _extra_params(self, options: dict[str, Any], model_config: ModelConfigDto) -> dict[str, Any]:
        extra_params = dict(model_config.extra_params or {})
        mapped = {
            "top_p": options.get("topP") or options.get("top_p"),
            "frequency_penalty": options.get("frequencyPenalty") or options.get("frequency_penalty"),
            "presence_penalty": options.get("presencePenalty") or options.get("presence_penalty"),
            "seed": options.get("seed"),
        }
        for key, value in mapped.items():
            if value is not None and value != "":
                extra_params[key] = _optional_float(value, value) if key != "seed" else _optional_int(value, value)
        response_format = options.get("responseFormat") or options.get("response_format")
        if isinstance(response_format, dict):
            extra_params["response_format"] = response_format
        elif str(response_format or "").upper() == "JSON":
            extra_params["response_format"] = {"type": "json_object"}
        stop = options.get("stopSequences") or options.get("stop")
        if isinstance(stop, str) and stop.strip():
            extra_params["stop"] = [item.strip() for item in stop.split("\n") if item.strip()]
        elif isinstance(stop, list) and stop:
            extra_params["stop"] = [str(item) for item in stop if str(item)]
        tool_choice = str(options.get("toolChoiceMode") or "").strip().lower()
        if tool_choice in {"auto", "required", "none"}:
            extra_params["tool_choice"] = tool_choice
        return extra_params

    def _llm_client(self, model_config: ModelConfigDto) -> Any:
        return self._llm_client_factory(
            ProviderChatConfig(
                provider_type=model_config.provider_type,
                base_url=model_config.provider_base_url,
                auth_config=model_config.provider_auth_config,
            )
        )

    def _complete_with_fallback(self, payload: dict[str, Any], model_config: ModelConfigDto) -> tuple[dict[str, Any], dict[str, Any]]:
        client = self._llm_client(model_config)
        request_model = str(payload.get("model") or model_config.model_id)
        try:
            return client.complete(payload), {}
        except Exception as exc:
            fallback_model = self._fallback_model(model_config)
            if not fallback_model or fallback_model == payload.get("model"):
                raise WorkflowExecutionError(f"LLM provider request failed: {_provider_request_error_message(exc)}") from exc
            primary_reason = _provider_request_error_message(exc)
            attempts = [{"model": request_model, "status": "failed", "reason": primary_reason}]
            fallback_payload = dict(payload)
            fallback_payload["model"] = fallback_model
            try:
                response = client.complete(fallback_payload)
            except Exception as fallback_exc:
                attempts.append(
                    {
                        "model": fallback_model,
                        "status": "failed",
                        "reason": _provider_request_error_message(fallback_exc),
                    }
                )
                raise WorkflowExecutionError(f"LLM provider request failed: {_provider_request_error_message(fallback_exc)}") from fallback_exc
            attempts.append({"model": fallback_model, "status": "succeeded"})
            return response, {
                "requestModel": request_model,
                "fallbackModel": fallback_model,
                "fallbackReason": primary_reason,
                "effectiveModel": fallback_model,
                "fallback": {"attempted": True, "attempts": attempts},
            }

    def _fallback_model(self, model_config: ModelConfigDto) -> str:
        extra_params = dict(model_config.extra_params or {})
        return str(extra_params.get("fallbackModel") or extra_params.get("fallback_model") or "").strip()

    def consume_last_call_debug(self) -> dict[str, Any]:
        debug = dict(self._last_call_debug)
        self._last_call_debug = {}
        return debug


def _redact_llm_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in payload.items():
        key_text = str(key)
        if key_text.lower() in {"authorization", "api_key", "apikey", "token", "secret", "password"}:
            redacted[key_text] = "***"
        else:
            redacted[key_text] = _json_safe(value)
    return redacted


def _llm_tool_call_evidence(result: ToolExecutionResult) -> dict[str, Any]:
    status = "SUCCEEDED" if result.success else "FAILED"
    evidence = {
        "toolName": result.name,
        "adapter": "mcp",
        "sanitizedInput": _redact_llm_payload(result.arguments),
        "latencyMs": int(result.latency_ms or 0),
        "status": status,
        "errorMessage": result.error_message,
        "retryCount": 0,
        "attempts": 1,
    }
    return {
        "callId": result.call_id,
        "toolName": result.name,
        "success": result.success,
        "content": result.content,
        "errorMessage": result.error_message,
        "latencyMs": int(result.latency_ms or 0),
        "arguments": _redact_llm_payload(result.arguments),
        "evidence": evidence,
    }


def _provider_request_error_message(exc: Exception) -> str:
    text = str(exc)
    lowered = text.lower()
    network_markers = (
        "nodename nor servname",
        "name or service not known",
        "temporary failure in name resolution",
        "connection refused",
        "connection reset",
        "connect error",
        "timed out",
        "timeout",
    )
    if any(marker in lowered for marker in network_markers):
        return "模型服务网络不可达，请检查模型服务 Base URL、网络/DNS 或代理配置"
    return text


def _usage_from_llm_response(response: Mapping[str, Any], payload: Mapping[str, Any], content: str) -> dict[str, Any]:
    usage = response.get("usage")
    if isinstance(usage, Mapping):
        input_tokens = _usage_int(usage, "inputTokens", "input_tokens", "prompt_tokens", "promptTokens")
        output_tokens = _usage_int(usage, "outputTokens", "output_tokens", "completion_tokens", "completionTokens")
        total_tokens = _usage_int(usage, "totalTokens", "total_tokens", "totalTokens")
        if total_tokens <= 0:
            total_tokens = input_tokens + output_tokens
        return {
            "inputTokens": input_tokens,
            "outputTokens": output_tokens,
            "totalTokens": total_tokens,
            "estimated": False,
        }
    prompt_text = _payload_text(payload)
    return _estimated_usage(prompt_text, content)


def _estimated_usage(input_text: str, output_text: str) -> dict[str, Any]:
    input_tokens = _estimate_tokens(input_text)
    output_tokens = _estimate_tokens(output_text)
    return {
        "inputTokens": input_tokens,
        "outputTokens": output_tokens,
        "totalTokens": input_tokens + output_tokens,
        "estimated": True,
    }


def _usage_int(usage: Mapping[str, Any], *keys: str) -> int:
    for key in keys:
        value = usage.get(key)
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        if parsed >= 0:
            return parsed
    return 0


def _payload_text(payload: Mapping[str, Any]) -> str:
    messages = payload.get("messages")
    if isinstance(messages, list):
        return "\n".join(str(item.get("content") or "") for item in messages if isinstance(item, Mapping))
    return str(payload)


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    # Mixed Chinese/English rough estimate; debug-only fallback when providers omit usage.
    return max(1, int(len(text) / 2.6))


def _has_enabled_knowledge_resource(config: Any) -> bool:
    if not isinstance(config, dict):
        return False
    resources = config.get("resources") or config.get("skillResources") or []
    if not isinstance(resources, list):
        return False
    for resource in resources:
        if not isinstance(resource, dict) or resource.get("enabled") is False:
            continue
        raw_type = str(resource.get("type") or resource.get("resourceType") or "").strip().upper().replace("-", "_")
        if raw_type in {"KNOWLEDGE", "KNOWLEDGE_BASE", "KNOWLEDGE_BASES", "KNOWLEDGEBASE"}:
            return True
    return False


def _is_llm_intent_node(node: dict[str, Any]) -> bool:
    if node["type"] != "INTENT_RECOGNITION":
        return False
    config = node.get("config")
    if not isinstance(config, dict):
        return False
    return str(config.get("classifierMode") or "").lower() == "llm"


def _is_llm_information_collection_node(node: dict[str, Any]) -> bool:
    if node["type"] != "INFORMATION_COLLECTION":
        return False
    config = node.get("config")
    if not isinstance(config, dict):
        return False
    return str(config.get("extractorMode") or "").lower() == "llm"


def _has_node_model_config(config: Any) -> bool:
    if not isinstance(config, Mapping):
        return False
    return bool(str(config.get("modelConfigId") or config.get("model_config_id") or "").strip())


def _chatflow_session_id(chatflow_id: int, run_id: int, input_data: dict[str, Any]) -> str:
    explicit = input_data.get("session_id") or input_data.get("sessionId")
    if explicit:
        return str(explicit)
    conversation_id = input_data.get("sys.conversation_id") or input_data.get("conversationId")
    if conversation_id:
        return str(conversation_id)
    return f"chatflow-{chatflow_id}-run-{run_id}"


def _chatflow_explicit_session_id(input_data: dict[str, Any]) -> str:
    explicit = input_data.get("session_id") or input_data.get("sessionId")
    if explicit:
        return str(explicit)
    conversation_id = input_data.get("sys.conversation_id") or input_data.get("conversationId")
    return str(conversation_id) if conversation_id else ""


def _normalize_chatflow_runtime_context(input_data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(input_data)
    message = str(_runtime_context_value(input_data, "sys.query", "USER_INPUT", "userMessage", "message", "query", "content") or "")
    channel = str(_runtime_context_value(input_data, "sys.channel", "channel") or "api")
    channel_id = str(_runtime_context_value(input_data, "sys.channel_id", "channelId", "channel_id") or channel)
    conversation_id = str(
        _runtime_context_value(input_data, "sys.conversation_id", "conversationId", "conversation_id", "sessionId", "session_id")
        or f"{channel}-{time_ns()}"
    )
    user_id = str(_runtime_context_value(input_data, "sys.user_id", "userId", "user_id") or f"{channel}-user")
    files = _runtime_context_value(input_data, "sys.files", "files") or []

    _set_missing_runtime_value(normalized, "userMessage", message)
    _set_missing_runtime_value(normalized, "USER_INPUT", message)
    _set_missing_runtime_value(normalized, "sys.query", message)
    _set_missing_runtime_value(normalized, "sys.channel", channel)
    _set_missing_runtime_value(normalized, "sys.channel_id", channel_id)
    _set_missing_runtime_value(normalized, "sys.conversation_id", conversation_id)
    _set_missing_runtime_value(normalized, "sys.user_id", user_id)
    _set_missing_runtime_value(normalized, "sys.files", files)

    sys_scope = dict(normalized.get("sys") or {}) if isinstance(normalized.get("sys"), Mapping) else {}
    _set_missing_runtime_value(sys_scope, "query", message)
    _set_missing_runtime_value(sys_scope, "channel", channel)
    _set_missing_runtime_value(sys_scope, "channel_id", channel_id)
    _set_missing_runtime_value(sys_scope, "conversation_id", conversation_id)
    _set_missing_runtime_value(sys_scope, "user_id", user_id)
    _set_missing_runtime_value(sys_scope, "files", files)
    normalized["sys"] = sys_scope
    return normalized


def _runtime_context_value(input_data: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = input_data.get(key)
        if value not in (None, ""):
            return value
        if "." not in key:
            continue
        scope, name = key.split(".", 1)
        scoped_values = input_data.get(scope)
        if isinstance(scoped_values, Mapping):
            scoped_value = scoped_values.get(name)
            if scoped_value not in (None, ""):
                return scoped_value
    return None


def _set_missing_runtime_value(target: dict[str, Any], key: str, value: Any) -> None:
    if target.get(key) in (None, ""):
        target[key] = value


def _needs_persisted_history(nodes: list[dict[str, Any]]) -> bool:
    return any(
        str(node.get("type") or "") in {"LLM", "INTENT_RECOGNITION", "INFORMATION_COLLECTION"}
        and _include_history_enabled(node.get("config"))
        for node in nodes
    )


def _include_history_enabled(config: Any) -> bool:
    if not isinstance(config, Mapping):
        return False
    return str(config.get("includeHistory") or "").lower() in {"1", "true", "yes", "on"}


def _chatflow_history_retention_limit(nodes: list[dict[str, Any]], input_data: Mapping[str, Any]) -> int:
    input_limit = _non_negative_int(_first_present(
        input_data,
        ("historyRetentionRounds", "history_retention_rounds", "sys.history_retention_rounds"),
    ), default=-1)
    if input_limit >= 0:
        return min(input_limit, 20)
    sys_payload = input_data.get("sys")
    if isinstance(sys_payload, Mapping):
        nested_limit = _non_negative_int(sys_payload.get("history_retention_rounds"), default=-1)
        if nested_limit >= 0:
            return min(nested_limit, 20)
    start_config = next((node.get("config") for node in nodes if str(node.get("type") or "") == "START"), {})
    if isinstance(start_config, Mapping):
        return min(_non_negative_int(_first_present(start_config, ("historyRetentionRounds", "history_retention_rounds")), default=3), 20)
    return 3


def _first_present(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in mapping:
            return mapping.get(key)
    return None


def _non_negative_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, parsed)


def _result_variable_scopes(result: Any) -> dict[str, dict[str, Any]]:
    scopes = getattr(result, "variable_scopes", None)
    if not isinstance(scopes, Mapping):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for scope, values in scopes.items():
        if isinstance(values, Mapping):
            normalized[str(scope)] = dict(values)
    return normalized


def _chatflow_session_status(run_status: str, output: Mapping[str, Any] | None = None) -> str:
    if run_status == "INTERRUPTED":
        interrupt = output.get("interrupt") if isinstance(output, Mapping) else None
        if isinstance(interrupt, Mapping) and str(interrupt.get("type") or "") == "TRANSFER_TO_HUMAN":
            return "handoff"
        return "waiting"
    if run_status == "SUCCEEDED":
        return "completed"
    if run_status == "FAILED":
        return "failed"
    return "active"


def _is_expired(value: Any) -> bool:
    return isinstance(value, datetime) and value < datetime.now()


def _message_events_from_node_runs(node_runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for node_run in node_runs:
        outputs = node_run.get("outputs") or {}
        if not isinstance(outputs, Mapping):
            continue
        raw_events = outputs.get("events") or []
        if not isinstance(raw_events, list):
            continue
        for raw_event in raw_events:
            if not isinstance(raw_event, Mapping):
                continue
            raw_type = str(raw_event.get("type") or "")
            if raw_type not in {"message_done", "handoff_requested"}:
                continue
            event = {
                "nodeKey": str(raw_event.get("nodeKey") or node_run.get("node_key") or ""),
                "content": str(raw_event.get("content") or ""),
                "rawType": raw_type,
            }
            if raw_type == "handoff_requested":
                event.update(
                    {
                        "handoffId": raw_event.get("handoffId"),
                        "queue": raw_event.get("queue"),
                        "priority": raw_event.get("priority"),
                        "reason": raw_event.get("reason"),
                    }
                )
            events.append(event)
    return events


def _stream_events_from_node_runs(node_runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for node_run in node_runs:
        outputs = node_run.get("outputs") or {}
        if not isinstance(outputs, Mapping):
            continue
        node_key = str(node_run.get("node_key") or "")
        raw_events = outputs.get("events") or []
        if isinstance(raw_events, list):
            for raw_event in raw_events:
                event = _stream_event_from_raw(raw_event, node_key)
                if event is not None:
                    events.append(event)
        if str(node_run.get("node_type") or "").upper() == "END":
            content = _stream_content_from_output(outputs)
            if content:
                events.append({"type": "message_delta", "nodeKey": node_key, "content": content})
                events.append({"type": "message_done", "nodeKey": node_key, "content": content})
    return events


def _stream_event_from_raw(raw_event: Any, fallback_node_key: str) -> dict[str, Any] | None:
    if not isinstance(raw_event, Mapping):
        return None
    event_type = str(raw_event.get("type") or "")
    if event_type not in {"message_delta", "message_done", "llm_delta", "agent_delta", "stream_error", "node_usage"}:
        return None
    event = {
        "type": event_type,
        "nodeKey": str(raw_event.get("nodeKey") or fallback_node_key),
        "content": str(raw_event.get("content") or ""),
    }
    if event_type == "stream_error":
        event["error"] = str(raw_event.get("error") or raw_event.get("message") or "")
    if event_type == "node_usage":
        for key in ("inputTokens", "outputTokens", "totalTokens", "costEstimate"):
            if key in raw_event:
                event[key] = raw_event.get(key)
    return event


def _stream_content_from_output(outputs: Mapping[str, Any]) -> str:
    preferred_keys = ("output", "answer", "final", "content")
    for key in preferred_keys:
        if key in outputs and _streamable_content(outputs.get(key)):
            return str(outputs.get(key))
    for key, value in outputs.items():
        if key in {"events", "toolCalls", "interrupt"}:
            continue
        if _streamable_content(value):
            return str(value)
    return ""


def _streamable_content(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool)) and str(value) != ""


def _merged_resume_data(resume_data: dict[str, Any], resume_schema: Any) -> dict[str, Any]:
    if not isinstance(resume_schema, Mapping):
        return resume_data
    merged = dict(resume_data)
    if "collected" in resume_schema and "collected" not in merged:
        merged["collected"] = resume_schema.get("collected")
    if "round" in resume_schema and "round" not in merged:
        merged["round"] = resume_schema.get("round")
    return merged


def _format_chatflow_event(event: dict[str, Any] | None) -> dict[str, Any] | None:
    if event is None:
        return None
    return {
        "id": int(event["id"]),
        "type": event["event_type"],
        "runId": int(event["run_id"]),
        "sequence": int(event["sequence"]),
        "nodeKey": event["node_key"],
        "payload": event["payload"] or {},
        "checkpointId": int(event["checkpoint_id"]) if event.get("checkpoint_id") else None,
        "createdAt": format_datetime(event["created_at"]),
    }


def _format_chatflow_checkpoint(checkpoint: dict[str, Any] | None) -> dict[str, Any] | None:
    if checkpoint is None:
        return None
    return {
        "id": int(checkpoint["id"]),
        "runId": int(checkpoint["run_id"]),
        "eventId": int(checkpoint["event_id"]) if checkpoint.get("event_id") else None,
        "pendingNodeKey": checkpoint["pending_node_key"],
        "resumeSchema": checkpoint["resume_schema"] or {},
        "status": checkpoint["status"],
        "expiresAt": format_datetime(checkpoint["expires_at"]) if checkpoint.get("expires_at") else None,
    }


def _optional_float(value: Any, fallback: Any) -> Any:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _optional_int(value: Any, fallback: Any) -> Any:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _optional_positive_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


_SENSITIVE_CONFIG_KEYS = {
    "apikey",
    "secret",
    "password",
    "accesstoken",
    "refreshtoken",
    "authorization",
    "bearertoken",
    "privatekey",
}


def _ensure_no_inline_secrets(nodes: list[dict[str, Any]]) -> None:
    for node in nodes:
        node_key = str(node.get("node_key") or node.get("nodeKey") or "")
        config = node.get("config")
        if not isinstance(config, Mapping):
            continue
        secret_path = _find_inline_secret(config, path=f"{node_key}.config")
        if secret_path:
            raise BizError(ErrorCode.BAD_REQUEST, f"Workflow graph config cannot store inline secret: {secret_path}")


def _find_inline_secret(value: Any, path: str) -> str:
    if isinstance(value, Mapping):
        header_secret = _header_secret_path(value, path)
        if header_secret:
            return header_secret
        for key, item in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}"
            if _is_sensitive_key(key_text) and _not_template_secret_value(item):
                return child_path
            nested = _find_inline_secret(item, child_path)
            if nested:
                return nested
    if isinstance(value, list):
        for index, item in enumerate(value):
            nested = _find_inline_secret(item, f"{path}[{index}]")
            if nested:
                return nested
    return ""


def _header_secret_path(value: Mapping[str, Any], path: str) -> str:
    header_name = value.get("name") or value.get("key")
    header_value = value.get("value")
    if header_name is None or header_value is None:
        return ""
    normalized = _normalize_key(str(header_name))
    if normalized in {"authorization", "apikey", "xapikey"} and _not_template_secret_value(header_value):
        return f"{path}.{header_name}"
    return ""


def _is_sensitive_key(key: str) -> bool:
    return _normalize_key(key) in _SENSITIVE_CONFIG_KEYS


def _normalize_key(key: str) -> str:
    return "".join(ch for ch in key.lower() if ch.isalnum())


def _not_template_secret_value(value: Any) -> bool:
    if value in (None, ""):
        return False
    if isinstance(value, str) and "{{" in value and "}}" in value:
        return False
    return True


def _publish_validation(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    nodes = snapshot.get("nodes") if isinstance(snapshot.get("nodes"), list) else []
    edges = snapshot.get("edges") if isinstance(snapshot.get("edges"), list) else []
    flow_type = str((snapshot.get("workflow") if isinstance(snapshot.get("workflow"), Mapping) else {}).get("flowType") or "")
    node_keys = {str(node.get("node_key") or "") for node in nodes if isinstance(node, Mapping)}
    errors: list[str] = []
    if "start" not in node_keys:
        errors.append("Workflow requires START node")
    if not any(str(node.get("type") or "") == "END" for node in nodes if isinstance(node, Mapping)):
        errors.append("Workflow requires END node")
    for node in nodes:
        if not isinstance(node, Mapping):
            continue
        node_key = str(node.get("node_key") or "")
        node_type = str(node.get("type") or "")
        config = node.get("config") if isinstance(node.get("config"), Mapping) else {}
        secret_path = _find_inline_secret(config, path=f"{node_key}.config")
        if secret_path:
            errors.append(f"Workflow graph config cannot store inline secret: {secret_path}")
        if node_type == "TRANSFER_TO_HUMAN":
            if flow_type != "CHATFLOW":
                errors.append(f"{node_key} TRANSFER_TO_HUMAN is Chatflow-only")
            if not str(config.get("queue") or "").strip():
                errors.append(f"{node_key} handoff queue is required")
        if node_type == "TOOL_CALL" and not (str(config.get("resourceId") or "").strip() or str(config.get("toolName") or "").strip()):
            errors.append(f"{node_key} tool resource is required")
        if node_type == "EXECUTE_WORKFLOW" and not str(config.get("targetWorkflowId") or "").strip():
            errors.append(f"{node_key} target workflow is required")
        if node_type == "KNOWLEDGE" and not str(config.get("knowledgeBaseId") or "").strip():
            errors.append(f"{node_key} knowledge base is required")
    branch_nodes = [dict(node) for node in nodes if isinstance(node, Mapping)]
    branch_edges = [dict(edge) for edge in edges if isinstance(edge, Mapping)]
    errors.extend(issue["message"] for issue in validate_node_endpoints(branch_nodes, branch_edges))
    errors.extend(issue["message"] for issue in validate_variable_references(branch_nodes))
    errors.extend(issue["message"] for issue in validate_node_contracts(branch_nodes))
    return {"valid": not errors, "errors": errors}


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return format_datetime(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


class _SnapshotWorkflowRepository:
    def __init__(
        self,
        base: WorkflowRepository,
        snapshot: Mapping[str, Any],
        publish_repository: WorkflowPublishRepository | None = None,
    ) -> None:
        self._base = base
        self._snapshot = snapshot
        self._publish_repository = publish_repository
        self._published_snapshot_cache: dict[int, Mapping[str, Any] | None] = {}
        workflow = snapshot.get("workflow") if isinstance(snapshot.get("workflow"), Mapping) else {}
        try:
            self._snapshot_workflow_id = int(workflow.get("id") or 0) if isinstance(workflow, Mapping) else 0
        except (TypeError, ValueError):
            self._snapshot_workflow_id = 0

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
        if workflow_id == self._snapshot_workflow_id:
            return self._snapshot
        if self._publish_repository is None:
            return None
        if workflow_id not in self._published_snapshot_cache:
            row = self._publish_repository.active_version(workflow_id, "WORKFLOW")
            snapshot = row.get("snapshot") if isinstance(row, Mapping) and isinstance(row.get("snapshot"), Mapping) else None
            self._published_snapshot_cache[workflow_id] = snapshot
        return self._published_snapshot_cache[workflow_id]
