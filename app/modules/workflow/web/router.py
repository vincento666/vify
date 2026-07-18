import json
import threading
import time
from collections.abc import Iterable, Mapping
from datetime import datetime
from functools import lru_cache
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.core.errors import BizError, ErrorCode
from app.core.host.context import RequestContext
from app.core.host.dependencies import get_request_context
from app.core.responses import success
from app.modules.audit.infra.repository import AuditRepository
from app.modules.agent.infra.repository import AgentRepository
from app.modules.handoff.domain.service import HandoffService
from app.modules.handoff.infra.repository import HandoffTicketRepository
from app.modules.knowledge.api.facade import KnowledgeFacade
from app.modules.mcp.api.facade import McpFacade
from app.modules.mcp.infra.repository import McpServerRepository
from app.modules.observe.domain.composer_run_debug import build_composer_run_debug
from app.modules.observe.web.router import ObserveService
from app.modules.provider.api.facade import ProviderModelFacade
from app.modules.runtime.domain.concurrency_limits import RuntimeConcurrencyGate, RuntimeConcurrencyLimits
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.domain.runtime_v2 import (
    ChatflowRuntimeV2Service,
    WorkflowRuntimeV2Service,
)
from app.modules.workflow.domain.runtime_invocation_gateway import RuntimeInvocationGateway
from app.modules.workflow.domain.resource_registry import WorkflowResourceRegistry
from app.modules.workflow.domain.api_resource_service import ApiResourceService
from app.modules.workflow.infra.api_resource_repository import ApiResourceRepository
from app.modules.workflow.infra.channel_repository import ChatflowChannelRepository
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.publish_repository import WorkflowPublishRepository
from app.modules.workflow.infra.realtime.redis_streams import (
    RedisRuntimeEventStreamBus,
    RuntimeEventStreamBus,
)
from app.modules.workflow.infra.repository import WorkflowRepository
from app.modules.runtime.infra.runtime_job_repository import RuntimeJobRepository, format_runtime_ops_job
from app.modules.workflow.runtime_job_worker import (
    build_chatflow_runtime_job_worker,
    build_workflow_runtime_job_worker,
)
from app.modules.workflow.web.schemas import (
    ChatflowChannelTestRequest,
    ChatflowChannelUpdateRequest,
    ChatflowMessageRequest,
    WorkflowCreateRequest,
    WorkflowCancelRequest,
    RuntimeJobActionRequest,
    WorkflowNodeRunRequest,
    WorkflowResumeRequest,
    WorkflowRunRequest,
    WorkflowUpdateRequest,
)

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])
chatflow_router = APIRouter(prefix="/api/v1/chatflows", tags=["chatflows"])
resource_router = APIRouter(prefix="/api/v1/workflow-resources", tags=["workflow-resources"])
runtime_v2_router = APIRouter(prefix="/api/v1/runtime-runs", tags=["runtime-runs"])
runtime_jobs_router = APIRouter(prefix="/api/v1/runtime-jobs", tags=["runtime-jobs"])
_RUNTIME_V2_INLINE_COMPLETION_WAIT_MS = 450


def get_workflow_service(
    session: Session = Depends(get_session),
    request_context: RequestContext = Depends(get_request_context),
) -> WorkflowService:
    return WorkflowService(
        WorkflowRepository(session),
        flow_type="WORKFLOW",
        agent_repository=AgentRepository(session),
        model_facade=ProviderModelFacade(session),
        knowledge_facade=KnowledgeFacade(session),
        mcp_tool_executor=McpFacade(session),
        api_tool_executor=ApiResourceService(ApiResourceRepository(session)),
        publish_repository=WorkflowPublishRepository(session),
        audit_repository=AuditRepository(session),
        request_context=request_context,
    )


def get_chatflow_service(
    session: Session = Depends(get_session),
    request_context: RequestContext = Depends(get_request_context),
) -> WorkflowService:
    return WorkflowService(
        WorkflowRepository(session),
        flow_type="CHATFLOW",
        agent_repository=AgentRepository(session),
        model_facade=ProviderModelFacade(session),
        knowledge_facade=KnowledgeFacade(session),
        mcp_tool_executor=McpFacade(session),
        api_tool_executor=ApiResourceService(ApiResourceRepository(session)),
        chatflow_state_repository=ChatflowStateRepository(session),
        channel_repository=ChatflowChannelRepository(session),
        publish_repository=WorkflowPublishRepository(session),
        handoff_service=HandoffService(HandoffTicketRepository(session)),
        audit_repository=AuditRepository(session),
        request_context=request_context,
    )


def _runtime_v2_llm_service(
    session: Session,
    *,
    flow_type: str,
    request_context: RequestContext | None = None,
    preferred_llm_agent_name: str | None = None,
) -> WorkflowService:
    return WorkflowService(
        WorkflowRepository(session),
        flow_type=flow_type,
        agent_repository=AgentRepository(session),
        model_facade=ProviderModelFacade(session),
        knowledge_facade=KnowledgeFacade(session),
        mcp_tool_executor=McpFacade(session),
        api_tool_executor=ApiResourceService(ApiResourceRepository(session)),
        request_context=request_context,
        preferred_llm_agent_name=preferred_llm_agent_name,
    )


def get_resource_registry(session: Session = Depends(get_session)) -> WorkflowResourceRegistry:
    return WorkflowResourceRegistry(
        mcp_repository=McpServerRepository(session),
        workflow_repository=WorkflowRepository(session),
        agent_repository=AgentRepository(session),
        api_resource_repository=ApiResourceRepository(session),
    )


def get_observe_service(session: Session = Depends(get_session)) -> ObserveService:
    return ObserveService(session)


def get_runtime_event_stream_bus(
    settings: Settings = Depends(get_settings),
) -> RuntimeEventStreamBus | None:
    if not settings.redis_url:
        return None
    return _redis_runtime_event_stream_bus(settings.redis_url)


@lru_cache(maxsize=4)
def _redis_runtime_event_stream_bus(redis_url: str) -> RuntimeEventStreamBus:
    return RedisRuntimeEventStreamBus.from_url(redis_url)


def get_chatflow_runtime_v2_service(
    session: Session = Depends(get_session),
    request_context: RequestContext = Depends(get_request_context),
    event_stream_bus: RuntimeEventStreamBus | None = Depends(get_runtime_event_stream_bus),
) -> ChatflowRuntimeV2Service:
    llm_service = _runtime_v2_llm_service(
        session, flow_type="CHATFLOW", request_context=request_context
    )
    return ChatflowRuntimeV2Service(
        WorkflowRepository(session),
        ChatflowStateRepository(session, event_stream_bus=event_stream_bus),
        runtime_job_repository=RuntimeJobRepository(session),
        publish_repository=WorkflowPublishRepository(session),
        knowledge_facade=KnowledgeFacade(session),
        llm_completer_resolver=llm_service.runtime_v2_llm_completer,
        agent_invoker_resolver=llm_service.runtime_v2_agent_invoker,
        mcp_tool_executor=llm_service.runtime_v2_mcp_tool_executor(),
        api_tool_executor=llm_service.runtime_v2_api_tool_executor(),
    )


def get_workflow_runtime_v2_service(
    session: Session = Depends(get_session),
    request_context: RequestContext = Depends(get_request_context),
    event_stream_bus: RuntimeEventStreamBus | None = Depends(get_runtime_event_stream_bus),
) -> WorkflowRuntimeV2Service:
    llm_service = _runtime_v2_llm_service(
        session, flow_type="WORKFLOW", request_context=request_context
    )
    return WorkflowRuntimeV2Service(
        WorkflowRepository(session),
        ChatflowStateRepository(session, event_stream_bus=event_stream_bus),
        WorkflowPublishRepository(session),
        runtime_job_repository=RuntimeJobRepository(session),
        knowledge_facade=KnowledgeFacade(session),
        llm_completer_resolver=llm_service.runtime_v2_llm_completer,
        agent_invoker_resolver=llm_service.runtime_v2_agent_invoker,
        mcp_tool_executor=llm_service.runtime_v2_mcp_tool_executor(),
        api_tool_executor=llm_service.runtime_v2_api_tool_executor(),
    )


@resource_router.get("")
def list_workflow_resources(
    flow_type: str = Query("WORKFLOW", alias="flowType"),
    resource_type: str | None = Query(None, alias="resourceType"),
    registry: WorkflowResourceRegistry = Depends(get_resource_registry),
) -> dict[str, Any]:
    return success(registry.list_resources(flow_type, resource_type))


@router.get("")
def list_workflows(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    status: str | None = None,
    service: WorkflowService = Depends(get_workflow_service),
) -> dict[str, Any]:
    return success(service.list(page, page_size, status))


@router.post("")
def create_workflow(
    request: WorkflowCreateRequest,
    service: WorkflowService = Depends(get_workflow_service),
) -> dict[str, Any]:
    return success(service.create(request))


@router.get("/{workflow_id}")
def get_workflow(
    workflow_id: int,
    service: WorkflowService = Depends(get_workflow_service),
) -> dict[str, Any]:
    return success(service.get(workflow_id))


@router.put("/{workflow_id}")
def update_workflow(
    workflow_id: int,
    request: WorkflowUpdateRequest,
    service: WorkflowService = Depends(get_workflow_service),
) -> dict[str, Any]:
    return success(service.update(workflow_id, request))


def _start_workflow_runtime_v2_gateway(
    workflow_id: int,
    request: WorkflowRunRequest,
    *,
    session: Session,
    service: WorkflowRuntimeV2Service,
    event_stream_bus: RuntimeEventStreamBus | None,
    request_context: RequestContext | None = None,
    request_thread_completion_enabled: bool = True,
    concurrency_limits: RuntimeConcurrencyLimits | None = None,
) -> dict[str, Any]:
    data = RuntimeInvocationGateway(service).start_only(
        owner_id=workflow_id,
        input_data=dict(request.input),
        idempotency_key=request.idempotency_key,
        version_id=request.version_id,
    )
    _attach_runtime_v2_transport(data, event_stream_bus)
    _attach_runtime_v2_response_refs(data)
    if not data.get("idempotentReplay"):
        AuditRepository(session).record(
            action="WORKFLOW_RUN",
            resource_type="WORKFLOW_RUN",
            resource_id=int(data["runId"]),
            metadata={
                "workflowId": workflow_id,
                "status": data.get("status"),
                **({"version": data.get("version")} if data.get("version") is not None else {}),
                **(
                    {"versionId": data.get("versionId")}
                    if data.get("versionId") is not None
                    else {}
                ),
            },
            request_context=request_context,
        )
        runtime_job_repository = RuntimeJobRepository(session)
        queue_context = _runtime_v2_queue_context(session, data, request_context)
        queue_decision = RuntimeConcurrencyGate(concurrency_limits or RuntimeConcurrencyLimits()).decide(
            runtime_job_repository.list_active_for_queue_gate(),
            owner_type="WORKFLOW",
            owner_id=workflow_id,
            tenant_id=queue_context["tenantId"],
            provider_keys=queue_context["providerKeys"],
        )
        data["queueState"] = queue_decision.to_payload()
        if not queue_decision.admitted:
            cancelled = service.cancel_run(
                int(data["runId"]),
                reason=f"runtime queue {queue_decision.status}: {queue_decision.reason}",
            )
            data["status"] = cancelled["status"]
            return data
        job = runtime_job_repository.enqueue(
            run_id=int(data["runId"]),
            owner_type="WORKFLOW",
            owner_id=workflow_id,
            job_type="runtime_v2_completion",
            payload=_runtime_v2_job_payload(
                data,
                owner_type="WORKFLOW",
                owner_id=workflow_id,
                idempotency_key=request.idempotency_key,
                workflowId=workflow_id,
                **queue_context,
            ),
        )
        if request_thread_completion_enabled and queue_decision.level == "none":
            _start_runtime_v2_completion_thread(
                session,
                int(data["runId"]),
                owner_type="WORKFLOW",
                job_id=int(job["id"]),
                event_stream_bus=event_stream_bus,
            )
    return data


@router.post("/{workflow_id}/runs")
def run_workflow(
    workflow_id: int,
    request: WorkflowRunRequest,
    session: Session = Depends(get_session),
    service: WorkflowRuntimeV2Service = Depends(get_workflow_runtime_v2_service),
    event_stream_bus: RuntimeEventStreamBus | None = Depends(get_runtime_event_stream_bus),
    request_context: RequestContext = Depends(get_request_context),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    return success(
        _start_workflow_runtime_v2_gateway(
            workflow_id,
            request,
            session=session,
            service=service,
            event_stream_bus=event_stream_bus,
            request_context=request_context,
            request_thread_completion_enabled=settings.runtime_v2_request_thread_completion_enabled,
            concurrency_limits=_runtime_v2_concurrency_limits(settings),
        )
    )


@router.post("/{workflow_id}/runs:stream")
def stream_workflow_run(
    workflow_id: int,
    request: WorkflowRunRequest,
    after_sequence: int = Query(default=0, alias="afterSequence", ge=0),
    heartbeat_ms: int = Query(default=1000, alias="heartbeatMs", ge=100, le=30000),
    test_limit: int | None = Query(default=None, alias="_testLimit", ge=1, le=1000),
    test_heartbeat_limit: int | None = Query(
        default=None, alias="_testHeartbeatLimit", ge=1, le=1000
    ),
    session: Session = Depends(get_session),
    service: WorkflowRuntimeV2Service = Depends(get_workflow_runtime_v2_service),
    event_stream_bus: RuntimeEventStreamBus | None = Depends(get_runtime_event_stream_bus),
    request_context: RequestContext = Depends(get_request_context),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    data = _start_workflow_runtime_v2_gateway(
        workflow_id,
        request,
        session=session,
        service=service,
        event_stream_bus=event_stream_bus,
        request_context=request_context,
        request_thread_completion_enabled=settings.runtime_v2_request_thread_completion_enabled,
        concurrency_limits=_runtime_v2_concurrency_limits(settings),
    )
    return StreamingResponse(
        _iter_runtime_v2_sse(
            service,
            run_id=int(data["runId"]),
            after_sequence=after_sequence,
            heartbeat_ms=heartbeat_ms,
            test_limit=test_limit,
            test_heartbeat_limit=test_heartbeat_limit,
            event_stream_bus=event_stream_bus,
        ),
        media_type="text/event-stream",
    )


@router.post("/{workflow_id}/runs-legacy")
def run_workflow_legacy(
    workflow_id: int,
    request: WorkflowRunRequest,
    service: WorkflowService = Depends(get_workflow_service),
) -> dict[str, Any]:
    return success(service.execute(workflow_id, request))


@router.get("/{workflow_id}/runs/{run_id}/debug")
def get_workflow_run_debug(
    workflow_id: int,
    run_id: int,
    service: ObserveService = Depends(get_observe_service),
) -> dict[str, Any]:
    try:
        detail = service.get_run(run_id)
    except NoResultFound as exc:
        raise BizError(ErrorCode.NOT_FOUND, "Workflow run not found") from exc
    if int(detail.get("workflowId") or 0) != workflow_id or detail.get("flowType") != "WORKFLOW":
        raise BizError(ErrorCode.NOT_FOUND, "Workflow run not found")
    debug = build_composer_run_debug(detail, owner_type="WORKFLOW", owner_id=workflow_id)
    _attach_runtime_v2_debug_version(debug)
    return success(debug)


@router.post("/{workflow_id}/published-runs")
def run_published_workflow(
    workflow_id: int,
    request: WorkflowRunRequest,
    service: WorkflowService = Depends(get_workflow_service),
) -> dict[str, Any]:
    return success(service.execute_published(workflow_id, request))


@router.post("/{workflow_id}/publish")
def publish_workflow(
    workflow_id: int,
    service: WorkflowService = Depends(get_workflow_service),
) -> dict[str, Any]:
    return success(service.publish(workflow_id))


@router.get("/{workflow_id}/versions")
def list_workflow_versions(
    workflow_id: int,
    service: WorkflowService = Depends(get_workflow_service),
) -> dict[str, Any]:
    return success(service.list_versions(workflow_id))


@router.post("/{workflow_id}/versions/{version_id}/rollback")
def rollback_workflow_version(
    workflow_id: int,
    version_id: int,
    service: WorkflowService = Depends(get_workflow_service),
) -> dict[str, Any]:
    return success(service.rollback_version(workflow_id, version_id))


@router.post("/{workflow_id}/nodes/{node_key}/runs")
def run_workflow_node(
    workflow_id: int,
    node_key: str,
    request: WorkflowNodeRunRequest,
    service: WorkflowService = Depends(get_workflow_service),
) -> dict[str, Any]:
    return success(service.run_node(workflow_id, node_key, request))


@router.delete("/{workflow_id}")
def delete_workflow(
    workflow_id: int,
    service: WorkflowService = Depends(get_workflow_service),
) -> dict[str, Any]:
    service.delete(workflow_id)
    return success(None)


@chatflow_router.get("")
def list_chatflows(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    status: str | None = None,
    service: WorkflowService = Depends(get_chatflow_service),
) -> dict[str, Any]:
    return success(service.list(page, page_size, status))


@chatflow_router.post("")
def create_chatflow(
    request: WorkflowCreateRequest,
    service: WorkflowService = Depends(get_chatflow_service),
) -> dict[str, Any]:
    return success(service.create(request))


@chatflow_router.get("/{chatflow_id}")
def get_chatflow(
    chatflow_id: int,
    service: WorkflowService = Depends(get_chatflow_service),
) -> dict[str, Any]:
    return success(service.get(chatflow_id))


@chatflow_router.put("/{chatflow_id}")
def update_chatflow(
    chatflow_id: int,
    request: WorkflowUpdateRequest,
    service: WorkflowService = Depends(get_chatflow_service),
) -> dict[str, Any]:
    return success(service.update(chatflow_id, request))


@chatflow_router.post("/{chatflow_id}/runs")
def run_chatflow(
    chatflow_id: int,
    request: WorkflowRunRequest,
    session: Session = Depends(get_session),
    service: ChatflowRuntimeV2Service = Depends(get_chatflow_runtime_v2_service),
    event_stream_bus: RuntimeEventStreamBus | None = Depends(get_runtime_event_stream_bus),
    request_context: RequestContext = Depends(get_request_context),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    return success(
        _start_chatflow_runtime_v2_gateway(
            chatflow_id,
            request,
            session=session,
            service=service,
            event_stream_bus=event_stream_bus,
            request_context=request_context,
            request_thread_completion_enabled=settings.runtime_v2_request_thread_completion_enabled,
            concurrency_limits=_runtime_v2_concurrency_limits(settings),
        )
    )


@chatflow_router.post("/{chatflow_id}/runs:stream")
def stream_chatflow_run(
    chatflow_id: int,
    request: WorkflowRunRequest,
    after_sequence: int = Query(default=0, alias="afterSequence", ge=0),
    heartbeat_ms: int = Query(default=1000, alias="heartbeatMs", ge=100, le=30000),
    test_limit: int | None = Query(default=None, alias="_testLimit", ge=1, le=1000),
    test_heartbeat_limit: int | None = Query(
        default=None, alias="_testHeartbeatLimit", ge=1, le=1000
    ),
    session: Session = Depends(get_session),
    service: ChatflowRuntimeV2Service = Depends(get_chatflow_runtime_v2_service),
    event_stream_bus: RuntimeEventStreamBus | None = Depends(get_runtime_event_stream_bus),
    request_context: RequestContext = Depends(get_request_context),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    data = _start_chatflow_runtime_v2_gateway(
        chatflow_id,
        request,
        session=session,
        service=service,
        event_stream_bus=event_stream_bus,
        request_context=request_context,
        request_thread_completion_enabled=settings.runtime_v2_request_thread_completion_enabled,
        concurrency_limits=_runtime_v2_concurrency_limits(settings),
    )
    return StreamingResponse(
        _iter_runtime_v2_sse(
            service,
            run_id=int(data["runId"]),
            after_sequence=after_sequence,
            heartbeat_ms=heartbeat_ms,
            test_limit=test_limit,
            test_heartbeat_limit=test_heartbeat_limit,
            event_stream_bus=event_stream_bus,
        ),
        media_type="text/event-stream",
    )


@chatflow_router.post("/{chatflow_id}/runs-legacy")
def run_chatflow_legacy(
    chatflow_id: int,
    http_request: Request,
    request: WorkflowRunRequest,
    service: WorkflowService = Depends(get_chatflow_service),
) -> Any:
    data = service.execute(chatflow_id, request)
    if _accepts_event_stream(http_request):
        return StreamingResponse(_iter_chatflow_run_sse(data), media_type="text/event-stream")
    return success(data)


def _start_chatflow_runtime_v2_gateway(
    chatflow_id: int,
    request: WorkflowRunRequest,
    *,
    session: Session,
    service: ChatflowRuntimeV2Service,
    event_stream_bus: RuntimeEventStreamBus | None,
    request_context: RequestContext | None = None,
    request_thread_completion_enabled: bool = True,
    concurrency_limits: RuntimeConcurrencyLimits | None = None,
) -> dict[str, Any]:
    data = RuntimeInvocationGateway(service).start_only(
        owner_id=chatflow_id,
        input_data=dict(request.input),
        idempotency_key=request.idempotency_key,
        version_id=request.version_id,
    )
    _attach_runtime_v2_transport(data, event_stream_bus)
    _attach_runtime_v2_response_refs(data)
    if not data.get("idempotentReplay"):
        AuditRepository(session).record(
            action="CHATFLOW_RUN",
            resource_type="CHATFLOW_RUN",
            resource_id=int(data["runId"]),
            metadata={
                "workflowId": chatflow_id,
                "chatflowId": chatflow_id,
                "status": data.get("status"),
                "runtimeVersion": 2,
                **({"version": data.get("version")} if data.get("version") is not None else {}),
                **(
                    {"versionId": data.get("versionId")}
                    if data.get("versionId") is not None
                    else {}
                ),
            },
            request_context=request_context,
        )
        runtime_job_repository = RuntimeJobRepository(session)
        queue_context = _runtime_v2_queue_context(session, data, request_context)
        queue_decision = RuntimeConcurrencyGate(concurrency_limits or RuntimeConcurrencyLimits()).decide(
            runtime_job_repository.list_active_for_queue_gate(),
            owner_type="CHATFLOW",
            owner_id=chatflow_id,
            tenant_id=queue_context["tenantId"],
            provider_keys=queue_context["providerKeys"],
        )
        data["queueState"] = queue_decision.to_payload()
        if not queue_decision.admitted:
            cancelled = service.cancel_run(
                int(data["runId"]),
                reason=f"runtime queue {queue_decision.status}: {queue_decision.reason}",
            )
            data["status"] = cancelled["status"]
            return data
        job = runtime_job_repository.enqueue(
            run_id=int(data["runId"]),
            owner_type="CHATFLOW",
            owner_id=chatflow_id,
            job_type="runtime_v2_completion",
            payload=_runtime_v2_job_payload(
                data,
                owner_type="CHATFLOW",
                owner_id=chatflow_id,
                idempotency_key=request.idempotency_key,
                chatflowId=chatflow_id,
                **queue_context,
            ),
        )
        if request_thread_completion_enabled and queue_decision.level == "none":
            _start_runtime_v2_completion_thread(
                session,
                int(data["runId"]),
                owner_type="CHATFLOW",
                job_id=int(job["id"]),
                event_stream_bus=event_stream_bus,
            )
    return data


@chatflow_router.post("/{chatflow_id}/messages")
def send_chatflow_message(
    chatflow_id: int,
    request: ChatflowMessageRequest,
    session: Session = Depends(get_session),
    service: ChatflowRuntimeV2Service = Depends(get_chatflow_runtime_v2_service),
    event_stream_bus: RuntimeEventStreamBus | None = Depends(get_runtime_event_stream_bus),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    input_data = _chatflow_message_runtime_input(chatflow_id, request)
    data = service.start_run(chatflow_id, input_data, request.idempotency_key, request.version_id)
    _attach_runtime_v2_transport(data, event_stream_bus)
    if not data.get("idempotentReplay"):
        job = RuntimeJobRepository(session).enqueue(
            run_id=int(data["runId"]),
            owner_type="CHATFLOW",
            owner_id=chatflow_id,
            job_type="runtime_v2_completion",
            payload=_runtime_v2_job_payload(
                data,
                owner_type="CHATFLOW",
                owner_id=chatflow_id,
                idempotency_key=request.idempotency_key,
                chatflowId=chatflow_id,
                entrypoint="messages",
            ),
        )
        job_id = int(job["id"])
        if (
            settings.runtime_v2_request_thread_completion_enabled
            and request.wait_timeout_ms >= _RUNTIME_V2_INLINE_COMPLETION_WAIT_MS
        ):
            build_chatflow_runtime_job_worker(
                session,
                worker_id=f"inline-chatflow-message-{data['runId']}-{time.time_ns()}",
                event_stream_bus=event_stream_bus,
            ).run_once(job_id=job_id)
        elif settings.runtime_v2_request_thread_completion_enabled:
            _start_runtime_v2_completion_thread(
                session,
                int(data["runId"]),
                owner_type="CHATFLOW",
                job_id=job_id,
                event_stream_bus=event_stream_bus,
            )
    result = _wait_for_runtime_v2_result(service, int(data["runId"]), request.wait_timeout_ms)
    return success(_chatflow_message_response(data, input_data, result, request.wait_timeout_ms))


@chatflow_router.get("/{chatflow_id}/runs/{run_id}/debug")
def get_chatflow_run_debug(
    chatflow_id: int,
    run_id: int,
    observe_service: ObserveService = Depends(get_observe_service),
    chatflow_service: WorkflowService = Depends(get_chatflow_service),
) -> dict[str, Any]:
    try:
        detail = observe_service.get_run(run_id)
    except NoResultFound as exc:
        raise BizError(ErrorCode.NOT_FOUND, "Chatflow run not found") from exc
    if int(detail.get("workflowId") or 0) != chatflow_id or detail.get("flowType") != "CHATFLOW":
        raise BizError(ErrorCode.NOT_FOUND, "Chatflow run not found")

    debug = build_composer_run_debug(detail, owner_type="CHATFLOW", owner_id=chatflow_id)
    _attach_runtime_v2_debug_version(debug)
    session_id = str(detail.get("sessionId") or "")
    session_state = (
        chatflow_service.get_session_state(chatflow_id, session_id) if session_id else {}
    )
    events = chatflow_service.list_run_events(chatflow_id, run_id)["list"]
    debug["session"] = {
        "sessionId": session_state.get("sessionId", session_id),
        "conversationId": session_state.get("conversationId", detail.get("sessionId", "")),
        "userId": session_state.get("userId", detail.get("userId", "")),
        "channel": session_state.get("channel", detail.get("channel", "")),
        "channelId": session_state.get("channelId", ""),
        "status": session_state.get("status", ""),
        "currentRunId": session_state.get("currentRunId", run_id),
    }
    debug["variables"] = session_state.get("variables", {})
    debug["waitingEvent"] = session_state.get("waitingEvent")
    debug["checkpoint"] = session_state.get("checkpoint")
    debug["events"] = events
    return success(debug)


@chatflow_router.post("/{chatflow_id}/published-runs")
def run_published_chatflow(
    chatflow_id: int,
    request: WorkflowRunRequest,
    service: WorkflowService = Depends(get_chatflow_service),
) -> dict[str, Any]:
    return success(service.execute_published(chatflow_id, request))


@chatflow_router.post("/{chatflow_id}/publish")
def publish_chatflow(
    chatflow_id: int,
    service: WorkflowService = Depends(get_chatflow_service),
) -> dict[str, Any]:
    return success(service.publish(chatflow_id))


@chatflow_router.get("/{chatflow_id}/versions")
def list_chatflow_versions(
    chatflow_id: int,
    service: WorkflowService = Depends(get_chatflow_service),
) -> dict[str, Any]:
    return success(service.list_versions(chatflow_id))


@chatflow_router.post("/{chatflow_id}/versions/{version_id}/rollback")
def rollback_chatflow_version(
    chatflow_id: int,
    version_id: int,
    service: WorkflowService = Depends(get_chatflow_service),
) -> dict[str, Any]:
    return success(service.rollback_version(chatflow_id, version_id))


@chatflow_router.post("/{chatflow_id}/nodes/{node_key}/runs")
def run_chatflow_node(
    chatflow_id: int,
    node_key: str,
    request: WorkflowNodeRunRequest,
    service: WorkflowService = Depends(get_chatflow_service),
) -> dict[str, Any]:
    return success(service.run_node(chatflow_id, node_key, request))


@chatflow_router.get("/{chatflow_id}/channels")
def list_chatflow_channels(
    chatflow_id: int,
    service: WorkflowService = Depends(get_chatflow_service),
) -> dict[str, Any]:
    return success(service.list_channels(chatflow_id))


@chatflow_router.put("/{chatflow_id}/channels/{channel_id}")
def update_chatflow_channel(
    chatflow_id: int,
    channel_id: str,
    request: ChatflowChannelUpdateRequest,
    service: WorkflowService = Depends(get_chatflow_service),
) -> dict[str, Any]:
    return success(service.update_channel(chatflow_id, channel_id, request))


@chatflow_router.post("/{chatflow_id}/channels/{channel_id}/test")
def test_chatflow_channel(
    chatflow_id: int,
    channel_id: str,
    request: ChatflowChannelTestRequest,
    service: WorkflowService = Depends(get_chatflow_service),
) -> dict[str, Any]:
    return success(service.test_channel(chatflow_id, channel_id, request))


@chatflow_router.get("/{chatflow_id}/sessions/{session_id}")
def get_chatflow_session(
    chatflow_id: int,
    session_id: str,
    service: WorkflowService = Depends(get_chatflow_service),
) -> dict[str, Any]:
    return success(service.get_session_state(chatflow_id, session_id))


@chatflow_router.get("/{chatflow_id}/sessions/{session_id}/events")
def list_chatflow_session_events(
    chatflow_id: int,
    session_id: str,
    after_event_id: int = Query(default=0, alias="afterEventId", ge=0),
    service: WorkflowService = Depends(get_chatflow_service),
) -> dict[str, Any]:
    return success(service.list_session_events(chatflow_id, session_id, after_event_id))


@chatflow_router.get("/{chatflow_id}/runs/{run_id}/events")
def list_chatflow_run_events(
    chatflow_id: int,
    run_id: int,
    service: WorkflowService = Depends(get_chatflow_service),
) -> dict[str, Any]:
    return success(service.list_run_events(chatflow_id, run_id))


@chatflow_router.post("/{chatflow_id}/runs/{run_id}/resume")
def resume_chatflow_run(
    chatflow_id: int,
    run_id: int,
    request: WorkflowResumeRequest,
    service: WorkflowService = Depends(get_chatflow_service),
) -> dict[str, Any]:
    return success(service.resume_run(chatflow_id, run_id, request))


@runtime_v2_router.get("")
def list_runtime_v2_runs(
    owner_type: str | None = Query(default=None, alias="ownerType"),
    state: str | None = Query(default=None),
    tenant_id: str | None = Query(default=None, alias="tenantId"),
    created_from: datetime | None = Query(default=None, alias="createdFrom"),
    created_to: datetime | None = Query(default=None, alias="createdTo"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    runs, total = WorkflowRepository(session).list_runtime_runs(
        page=page,
        page_size=page_size,
        owner_type=owner_type,
        state=state,
        tenant_id=tenant_id,
        created_from=created_from,
        created_to=created_to,
    )
    return success({"list": runs, "total": total, "page": page, "pageSize": page_size})


@runtime_jobs_router.get("")
def list_runtime_jobs(
    owner_type: str | None = Query(default=None, alias="ownerType"),
    status: str | None = Query(default=None),
    tenant_id: str | None = Query(default=None, alias="tenantId"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    jobs, total = RuntimeJobRepository(session).list_jobs(
        page=page,
        page_size=page_size,
        owner_type=owner_type,
        status=status,
        tenant_id=tenant_id,
    )
    return success({"list": jobs, "total": total, "page": page, "pageSize": page_size})


@runtime_jobs_router.get("/dlq")
def list_runtime_jobs_dlq(
    owner_type: str | None = Query(default=None, alias="ownerType"),
    tenant_id: str | None = Query(default=None, alias="tenantId"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    jobs, total = RuntimeJobRepository(session).list_jobs(
        page=page,
        page_size=page_size,
        owner_type=owner_type,
        status="FAILED",
        tenant_id=tenant_id,
    )
    return success({"list": jobs, "total": total, "page": page, "pageSize": page_size})


@runtime_jobs_router.post("/{job_id}/retry")
def retry_runtime_job_dlq(
    job_id: int,
    session: Session = Depends(get_session),
    request_context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    result = _run_runtime_job_action(session, job_id, "retry")
    _record_runtime_ops_audit(
        session,
        action="RUNTIME_OPS_RETRY_JOB",
        resource_type="runtime_job",
        resource_id=job_id,
        metadata={"jobId": job_id, "resultStatus": result.get("status")},
        request_context=request_context,
    )
    return success(result)


@runtime_jobs_router.post("/{job_id}/ignore")
def ignore_runtime_job_dlq(
    job_id: int,
    request: RuntimeJobActionRequest | None = None,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    reason = request.reason if request is not None and request.reason else "operator ignored"
    return success(_run_runtime_job_action(session, job_id, "ignore", reason=reason))


@runtime_jobs_router.post("/{job_id}/mark-resolved")
def mark_runtime_job_dlq_resolved(
    job_id: int,
    request: RuntimeJobActionRequest | None = None,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    reason = request.reason if request is not None and request.reason else "operator marked resolved"
    return success(_run_runtime_job_action(session, job_id, "mark-resolved", reason=reason))


@runtime_jobs_router.post("/{job_id}/reopen")
def reopen_runtime_job_dlq(
    job_id: int,
    request: RuntimeJobActionRequest | None = None,
    session: Session = Depends(get_session),
    request_context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    reason = request.reason if request is not None and request.reason else "operator reopened"
    result = _run_runtime_job_action(session, job_id, "reopen", reason=reason)
    _record_runtime_ops_audit(
        session,
        action="RUNTIME_OPS_REOPEN_DLQ",
        resource_type="runtime_job",
        resource_id=job_id,
        metadata={"jobId": job_id, "reason": reason, "resultStatus": result.get("status")},
        request_context=request_context,
    )
    return success(result)


def _run_runtime_job_action(
    session: Session,
    job_id: int,
    action: str,
    *,
    reason: str = "",
) -> dict[str, Any]:
    repository = RuntimeJobRepository(session)
    try:
        if action == "retry":
            return format_runtime_ops_job(repository.retry_dlq(job_id))
        if action == "ignore":
            return format_runtime_ops_job(repository.ignore_dlq(job_id, reason=reason or "operator ignored"))
        if action == "mark-resolved":
            return format_runtime_ops_job(
                repository.mark_dlq_resolved(job_id, reason=reason or "operator marked resolved")
            )
        if action == "reopen":
            return format_runtime_ops_job(repository.reopen_dlq(job_id, reason=reason or "operator reopened"))
    except RuntimeError as exc:
        raise BizError(ErrorCode.BAD_REQUEST, str(exc)) from exc
    raise BizError(ErrorCode.BAD_REQUEST, f"Unsupported runtime job action: {action}")


def _record_runtime_ops_audit(
    session: Session,
    *,
    action: str,
    resource_type: str,
    resource_id: int,
    metadata: dict[str, Any],
    request_context: RequestContext,
) -> None:
    AuditRepository(session).record(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        status="succeeded",
        metadata=metadata,
        request_context=request_context,
    )


@runtime_v2_router.get("/{run_id}")
def get_runtime_v2_run(
    run_id: int,
    service: ChatflowRuntimeV2Service = Depends(get_chatflow_runtime_v2_service),
) -> dict[str, Any]:
    return success(service.get_result(run_id))


@runtime_v2_router.get("/{run_id}/result")
def get_runtime_v2_result(
    run_id: int,
    service: ChatflowRuntimeV2Service = Depends(get_chatflow_runtime_v2_service),
) -> dict[str, Any]:
    return success(service.get_result(run_id))


@runtime_v2_router.get("/{run_id}/events")
def list_runtime_v2_events(
    run_id: int,
    after_sequence: int = Query(default=0, alias="afterSequence", ge=0),
    service: ChatflowRuntimeV2Service = Depends(get_chatflow_runtime_v2_service),
) -> dict[str, Any]:
    return success(service.list_events(run_id, after_sequence=after_sequence))


@runtime_v2_router.get("/{run_id}/nodes")
def list_runtime_v2_nodes(
    run_id: int,
    service: ChatflowRuntimeV2Service = Depends(get_chatflow_runtime_v2_service),
) -> dict[str, Any]:
    return success(service.list_nodes(run_id))


@runtime_v2_router.get("/{run_id}/events/stream")
def stream_runtime_v2_events(
    run_id: int,
    after_sequence: int = Query(default=0, alias="afterSequence", ge=0),
    heartbeat_ms: int = Query(default=1000, alias="heartbeatMs", ge=100, le=30000),
    test_limit: int | None = Query(default=None, alias="_testLimit", ge=1, le=1000),
    test_heartbeat_limit: int | None = Query(
        default=None, alias="_testHeartbeatLimit", ge=1, le=1000
    ),
    service: ChatflowRuntimeV2Service = Depends(get_chatflow_runtime_v2_service),
    event_stream_bus: RuntimeEventStreamBus | None = Depends(get_runtime_event_stream_bus),
) -> StreamingResponse:
    return StreamingResponse(
        _iter_runtime_v2_sse(
            service,
            run_id=run_id,
            after_sequence=after_sequence,
            heartbeat_ms=heartbeat_ms,
            test_limit=test_limit,
            test_heartbeat_limit=test_heartbeat_limit,
            event_stream_bus=event_stream_bus,
        ),
        media_type="text/event-stream",
    )


@runtime_v2_router.post("/{run_id}/resume")
def resume_runtime_v2_run(
    run_id: int,
    request: WorkflowResumeRequest,
    service: ChatflowRuntimeV2Service = Depends(get_chatflow_runtime_v2_service),
    session: Session = Depends(get_session),
    request_context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    result = service.resume_run(run_id, dict(request.resume_data), request.idempotency_key)
    _record_runtime_ops_audit(
        session,
        action="RUNTIME_OPS_RESUME_RUN",
        resource_type="runtime_run",
        resource_id=run_id,
        metadata={
            "runId": run_id,
            "idempotencyKey": request.idempotency_key or "",
            "resultStatus": result.get("status"),
        },
        request_context=request_context,
    )
    return success(result)


@runtime_v2_router.post("/{run_id}/cancel")
def cancel_runtime_v2_run(
    run_id: int,
    request: WorkflowCancelRequest | None = None,
    service: ChatflowRuntimeV2Service = Depends(get_chatflow_runtime_v2_service),
    session: Session = Depends(get_session),
    request_context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    reason = request.reason if request is not None else "cancelled by operator"
    deadline_ms = request.deadline_ms if request is not None else 1000
    result = service.cancel_run(run_id, reason=reason, deadline_ms=deadline_ms)
    _record_runtime_ops_audit(
        session,
        action="RUNTIME_OPS_CANCEL_RUN",
        resource_type="runtime_run",
        resource_id=run_id,
        metadata={"runId": run_id, "reason": reason, "deadlineMs": deadline_ms, "resultStatus": result.get("status")},
        request_context=request_context,
    )
    return success(result)


def _accepts_event_stream(request: Request) -> bool:
    return "text/event-stream" in str(request.headers.get("accept") or "").lower()


def _start_runtime_v2_completion_thread(
    session: Session,
    run_id: int,
    *,
    owner_type: str = "CHATFLOW",
    job_id: int | None = None,
    event_stream_bus: RuntimeEventStreamBus | None = None,
) -> None:
    bind = session.get_bind()
    if bind is None:
        return
    factory = sessionmaker(bind=bind, autoflush=False, autocommit=False, expire_on_commit=False)

    def complete() -> None:
        worker_id = f"inline-runtime-v2-{run_id}-{time.time_ns()}"
        with factory() as background_session:
            if job_id is not None and owner_type.upper() == "WORKFLOW":
                build_workflow_runtime_job_worker(
                    background_session,
                    worker_id=worker_id,
                    event_stream_bus=event_stream_bus,
                ).run_once(job_id=job_id)
                return
            if job_id is not None and owner_type.upper() == "CHATFLOW":
                build_chatflow_runtime_job_worker(
                    background_session,
                    worker_id=worker_id,
                    event_stream_bus=event_stream_bus,
                ).run_once(job_id=job_id)
                return
            llm_service = _runtime_v2_llm_service(background_session, flow_type="CHATFLOW")
            ChatflowRuntimeV2Service(
                WorkflowRepository(background_session),
                ChatflowStateRepository(background_session, event_stream_bus=event_stream_bus),
                publish_repository=WorkflowPublishRepository(background_session),
                knowledge_facade=KnowledgeFacade(background_session),
                llm_completer_resolver=llm_service.runtime_v2_llm_completer,
                agent_invoker_resolver=llm_service.runtime_v2_agent_invoker,
                mcp_tool_executor=llm_service.runtime_v2_mcp_tool_executor(),
                api_tool_executor=llm_service.runtime_v2_api_tool_executor(),
            ).complete_run(run_id)

    threading.Thread(target=complete, daemon=True).start()


def _runtime_v2_job_payload(
    data: dict[str, Any],
    *,
    owner_type: str,
    owner_id: int,
    idempotency_key: str | None,
    **extra: Any,
) -> dict[str, Any]:
    payload = {
        "runId": int(data["runId"]),
        "ownerType": owner_type.upper(),
        "ownerId": owner_id,
        "versionId": data.get("versionId"),
        "idempotencyKey": idempotency_key or "",
        "idempotencyLayer": "run",
    }
    payload.update(extra)
    return payload


def _runtime_v2_concurrency_limits(settings: Settings) -> RuntimeConcurrencyLimits:
    return RuntimeConcurrencyLimits(
        tenant_active_limit=settings.runtime_v2_tenant_active_limit,
        workflow_active_limit=settings.runtime_v2_workflow_active_limit,
        chatflow_active_limit=settings.runtime_v2_chatflow_active_limit,
        worker_running_limit=settings.runtime_v2_worker_running_limit,
        provider_active_limit=settings.runtime_v2_provider_active_limit,
        queue_capacity_limit=settings.runtime_v2_queue_capacity_limit,
    )


def _runtime_v2_queue_context(
    session: Session,
    data: dict[str, Any],
    request_context: RequestContext | None,
) -> dict[str, Any]:
    tenant_id = request_context.tenant_id if request_context is not None else "local"
    run = WorkflowRepository(session).get_run(int(data["runId"]))
    input_data = dict(run.get("input") or {}) if run else {}
    runtime = input_data.get("_runtimeV2") if isinstance(input_data.get("_runtimeV2"), Mapping) else {}
    definition = runtime.get("definition") if isinstance(runtime, Mapping) else {}
    nodes = definition.get("nodes") if isinstance(definition, Mapping) and isinstance(definition.get("nodes"), list) else []
    return {
        "tenantId": tenant_id,
        "providerKeys": _runtime_v2_provider_keys(nodes),
    }


def _runtime_v2_provider_keys(nodes: Iterable[Mapping[str, Any]]) -> list[str]:
    keys: list[str] = []
    for node in nodes:
        node_type = str(node.get("type") or "").upper()
        config = node.get("config") if isinstance(node.get("config"), Mapping) else {}
        if node_type == "LLM":
            keys.append("llm:" + str(config.get("modelConfigId") or config.get("model_config_id") or config.get("model") or "default"))
        elif node_type == "API_CALL":
            keys.append("api:" + str(config.get("resourceId") or config.get("resource_id") or config.get("url") or config.get("endpoint") or "direct"))
        elif node_type == "TOOL_CALL":
            keys.append("tool:" + str(config.get("resourceId") or config.get("resource_id") or config.get("toolName") or config.get("name") or "default"))
        elif node_type == "KNOWLEDGE":
            keys.append("knowledge:" + str(config.get("knowledgeBaseId") or config.get("knowledge_base_id") or "default"))
    return sorted(set(keys))


def _chatflow_message_runtime_input(
    chatflow_id: int, request: ChatflowMessageRequest
) -> dict[str, Any]:
    message = request.message
    channel = str(request.channel or "api")
    session_id = str(
        request.session_id
        or request.conversation_id
        or f"chatflow-{chatflow_id}-session-{time.time_ns()}"
    )
    conversation_id = str(request.conversation_id or session_id)
    channel_id = str(request.channel_id or channel)
    input_data = dict(request.input)
    input_data.update(
        {
            "message": message,
            "userMessage": message,
            "USER_INPUT": message,
            "sys.query": message,
            "sessionId": session_id,
            "conversationId": conversation_id,
            "sys.session_id": session_id,
            "sys.conversation_id": conversation_id,
            "channel": channel,
            "channelId": channel_id,
            "sys.channel": channel,
            "sys.channel_id": channel_id,
            "files": request.files,
            "sys.files": request.files,
            "metadata": request.metadata,
        }
    )
    if request.user_id:
        input_data["userId"] = request.user_id
        input_data["sys.user_id"] = request.user_id
    return input_data


def _wait_for_runtime_v2_result(
    service: ChatflowRuntimeV2Service,
    run_id: int,
    wait_timeout_ms: int,
) -> dict[str, Any]:
    deadline = time.monotonic() + (wait_timeout_ms / 1000)
    latest = service.get_result(run_id)
    while wait_timeout_ms > 0 and time.monotonic() <= deadline:
        status = str(latest.get("status") or "").upper()
        if status in {"INTERRUPTED", "FAILED", "CANCELLED"}:
            return latest
        if status == "SUCCEEDED":
            answer = _chatflow_gateway_answer(dict(latest.get("output") or {}))
            if not answer or _runtime_v2_has_event(service, run_id, "assistant_message"):
                return latest
        time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
        latest = service.get_result(run_id)
    return latest


def _runtime_v2_has_event(service: ChatflowRuntimeV2Service, run_id: int, event_type: str) -> bool:
    try:
        events = service.list_events(run_id).get("list") or []
    except Exception:
        return False
    return any(isinstance(event, dict) and event.get("type") == event_type for event in events)


def _chatflow_message_response(
    start: dict[str, Any],
    input_data: dict[str, Any],
    result: dict[str, Any],
    wait_timeout_ms: int,
) -> dict[str, Any]:
    run_id = int(start["runId"])
    status = str(result.get("status") or start.get("status") or "RUNNING")
    output = dict(result.get("output") or {})
    checkpoint = result.get("checkpoint") if isinstance(result.get("checkpoint"), dict) else None
    answer = _chatflow_gateway_answer(output)
    response = {
        "sessionId": str(start.get("sessionId") or input_data.get("sys.session_id") or ""),
        "conversationId": str(
            input_data.get("sys.conversation_id") or start.get("sessionId") or ""
        ),
        "runId": run_id,
        "status": status,
        "answer": answer or None,
        "result": dict(result.get("result") or output),
        "output": output,
        "latencyMs": _chatflow_response_latency_ms(result),
        "usage": _chatflow_response_usage(result),
        "retryable": bool(result.get("retryable")),
        "events": _chatflow_response_events(result),
        "requiresInput": status.upper() == "INTERRUPTED" or checkpoint is not None,
        "checkpoint": checkpoint,
        "statusRef": f"/api/v1/runtime-runs/{run_id}",
        "eventsRef": start.get("eventsRef") or f"/api/v1/runtime-runs/{run_id}/events",
        "eventStreamRef": start.get("eventStreamRef")
        or f"/api/v1/runtime-runs/{run_id}/events/stream?afterSequence=0",
        "nodesRef": start.get("nodesRef") or f"/api/v1/runtime-runs/{run_id}/nodes",
        "resultRef": start.get("resultRef") or f"/api/v1/runtime-runs/{run_id}/result",
        "idempotentReplay": bool(start.get("idempotentReplay")),
        "waitTimedOut": wait_timeout_ms > 0 and status.upper() == "RUNNING",
        "transport": start.get("transport") or {},
        "error": str(result.get("error") or ""),
    }
    failure = result.get("failure")
    if isinstance(failure, Mapping):
        response["failure"] = dict(failure)
        response["errorCode"] = str(failure.get("code") or "")
    if start.get("versionId") is not None:
        response["versionId"] = start.get("versionId")
        response["version"] = start.get("version")
    return response


def _chatflow_response_latency_ms(result: dict[str, Any]) -> int:
    try:
        parsed = int(result.get("latencyMs") or 0)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed >= 0 else 0


def _chatflow_response_usage(result: dict[str, Any]) -> dict[str, Any]:
    usage = result.get("usage") if isinstance(result.get("usage"), dict) else {}
    return {
        "inputTokens": _chatflow_response_usage_int(usage.get("inputTokens")),
        "outputTokens": _chatflow_response_usage_int(usage.get("outputTokens")),
        "totalTokens": _chatflow_response_usage_int(usage.get("totalTokens")),
        "estimated": bool(usage.get("estimated", False)),
    }


def _chatflow_response_usage_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed >= 0 else 0


def _chatflow_response_events(result: dict[str, Any]) -> list[dict[str, Any]]:
    events = result.get("events") if isinstance(result.get("events"), list) else []
    return [dict(event) for event in events if isinstance(event, dict)]


def _chatflow_gateway_answer(output: dict[str, Any]) -> str:
    if _chatflow_gateway_no_reply(output):
        return ""
    for key in ("answer", "final", "output", "content", "message", "text"):
        value = output.get(key)
        if value is not None and str(value).strip():
            return str(value)
    for value in output.values():
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _chatflow_gateway_no_reply(output: dict[str, Any]) -> bool:
    no_reply = output.get("noReply") or output.get("no_reply")
    if isinstance(no_reply, bool):
        return no_reply
    if no_reply is not None and str(no_reply).strip().lower() in {"1", "true", "yes", "on"}:
        return True
    side_effect_only = output.get("sideEffectOnly") or output.get("side_effect_only")
    if isinstance(side_effect_only, bool):
        return side_effect_only and str(output.get("summary") or "") == "side_effect_only_completed"
    return (
        side_effect_only is not None
        and str(side_effect_only).strip().lower() in {"1", "true", "yes", "on"}
        and str(output.get("summary") or "") == "side_effect_only_completed"
    )


def _iter_runtime_v2_sse(
    service: ChatflowRuntimeV2Service,
    *,
    run_id: int,
    after_sequence: int,
    heartbeat_ms: int,
    test_limit: int | None,
    test_heartbeat_limit: int | None,
    event_stream_bus: RuntimeEventStreamBus | None = None,
) -> Iterable[str]:
    last_sequence = after_sequence
    emitted = 0
    heartbeats = 0
    while True:
        rows = runtime_v2_stream_events(
            service,
            event_stream_bus=event_stream_bus,
            run_id=run_id,
            after_sequence=last_sequence,
            heartbeat_ms=heartbeat_ms,
            count=test_limit or 100,
        )
        if rows:
            for row in rows:
                last_sequence = int(row["sequence"])
                yield _sse_data(row)
                emitted += 1
                if test_limit is not None and emitted >= test_limit:
                    return
            continue
        yield ": heartbeat\n\n"
        heartbeats += 1
        if test_heartbeat_limit is not None and heartbeats >= test_heartbeat_limit:
            return
        time.sleep(heartbeat_ms / 1000)


def runtime_v2_stream_events(
    service: ChatflowRuntimeV2Service,
    *,
    event_stream_bus: RuntimeEventStreamBus | None,
    run_id: int,
    after_sequence: int,
    heartbeat_ms: int,
    count: int,
) -> list[dict[str, Any]]:
    if event_stream_bus is not None:
        try:
            rows = event_stream_bus.read_after(
                run_id=run_id,
                after_sequence=after_sequence,
                count=count,
                block_ms=0,
            )
        except Exception:
            rows = []
        if rows:
            return _reconcile_runtime_v2_live_rows(
                service,
                run_id=run_id,
                after_sequence=after_sequence,
                rows=rows,
            )
    rows = _runtime_v2_durable_stream_rows(service, run_id=run_id, after_sequence=after_sequence)
    if rows:
        return rows
    if event_stream_bus is not None:
        try:
            rows = event_stream_bus.read_after(
                run_id=run_id,
                after_sequence=after_sequence,
                count=count,
                block_ms=heartbeat_ms,
            )
        except Exception:
            rows = []
        if rows:
            return _reconcile_runtime_v2_live_rows(
                service,
                run_id=run_id,
                after_sequence=after_sequence,
                rows=rows,
            )
    return _runtime_v2_durable_stream_rows(service, run_id=run_id, after_sequence=after_sequence)


def _reconcile_runtime_v2_live_rows(
    service: ChatflowRuntimeV2Service,
    *,
    run_id: int,
    after_sequence: int,
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    ordered = _ordered_runtime_v2_stream_rows(rows)
    if not _runtime_v2_stream_has_sequence_gap(ordered, after_sequence=after_sequence):
        return ordered
    durable_rows = _runtime_v2_durable_stream_rows(
        service,
        run_id=run_id,
        after_sequence=after_sequence,
        fresh=True,
    )
    return durable_rows or ordered


def _runtime_v2_durable_stream_rows(
    service: ChatflowRuntimeV2Service,
    *,
    run_id: int,
    after_sequence: int,
    fresh: bool = False,
) -> list[dict[str, Any]]:
    if fresh:
        fresh_reader = getattr(service, "list_events_fresh", None)
        if callable(fresh_reader):
            return _ordered_runtime_v2_stream_rows(list(fresh_reader(run_id, after_sequence=after_sequence)["list"]))
    return _ordered_runtime_v2_stream_rows(list(service.list_events(run_id, after_sequence=after_sequence)["list"]))


def _ordered_runtime_v2_stream_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows_by_sequence: dict[int, dict[str, Any]] = {}
    for row in rows:
        rows_by_sequence.setdefault(int(row["sequence"]), row)
    return [rows_by_sequence[sequence] for sequence in sorted(rows_by_sequence)]


def _runtime_v2_stream_has_sequence_gap(rows: list[dict[str, Any]], *, after_sequence: int) -> bool:
    expected_sequence = after_sequence + 1
    for row in rows:
        if int(row["sequence"]) != expected_sequence:
            return True
        expected_sequence += 1
    return False


_runtime_v2_stream_events = runtime_v2_stream_events


def _attach_runtime_v2_transport(
    data: dict[str, Any], event_stream_bus: RuntimeEventStreamBus | None
) -> None:
    transport = data.get("transport")
    if not isinstance(transport, dict):
        return
    if event_stream_bus is None:
        transport.setdefault("redisStreams", "not_configured")
        return
    transport["redisStreams"] = "enabled"
    transport["redisPubsub"] = "redis_streams_realtime_buffer"


def _attach_runtime_v2_response_refs(data: dict[str, Any]) -> None:
    run_id = data.get("runId")
    data["runtimeVersion"] = 2
    data["runtimeRefs"] = {
        "runId": run_id,
        "statusRef": data.get("statusRef") or f"/api/v1/runtime-runs/{run_id}",
        "eventsRef": data.get("eventsRef") or f"/api/v1/runtime-runs/{run_id}/events",
        "eventStreamRef": data.get("eventStreamRef")
        or f"/api/v1/runtime-runs/{run_id}/events/stream?afterSequence=0",
        "nodesRef": data.get("nodesRef") or f"/api/v1/runtime-runs/{run_id}/nodes",
        "resultRef": data.get("resultRef") or f"/api/v1/runtime-runs/{run_id}/result",
    }


def _iter_chatflow_run_sse(data: dict[str, Any]) -> Iterable[str]:
    for event in data.get("streamEvents") or []:
        if isinstance(event, dict):
            yield _sse_data(event)
    yield _sse_data(
        {
            "type": "run_done",
            "runId": data.get("runId"),
            "status": data.get("status"),
            "output": data.get("output") or {},
            "sessionId": data.get("sessionId"),
            "sessionStatus": data.get("sessionStatus"),
        }
    )


def _sse_data(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _attach_runtime_v2_debug_version(debug: dict[str, Any]) -> None:
    input_data = debug.get("input") if isinstance(debug.get("input"), dict) else {}
    metadata = (
        input_data.get("_runtimeV2") if isinstance(input_data.get("_runtimeV2"), dict) else {}
    )
    if metadata.get("versionId") is not None:
        debug["versionId"] = metadata.get("versionId")
        debug["version"] = metadata.get("version")


@chatflow_router.delete("/{chatflow_id}")
def delete_chatflow(
    chatflow_id: int,
    service: WorkflowService = Depends(get_chatflow_service),
) -> dict[str, Any]:
    service.delete(chatflow_id)
    return success(None)
