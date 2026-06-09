from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

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
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.domain.resource_registry import WorkflowResourceRegistry
from app.modules.workflow.domain.api_resource_service import ApiResourceService
from app.modules.workflow.infra.api_resource_repository import ApiResourceRepository
from app.modules.workflow.infra.channel_repository import ChatflowChannelRepository
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.publish_repository import WorkflowPublishRepository
from app.modules.workflow.infra.repository import WorkflowRepository
from app.modules.workflow.web.schemas import (
    ChatflowChannelTestRequest,
    ChatflowChannelUpdateRequest,
    WorkflowCreateRequest,
    WorkflowNodeRunRequest,
    WorkflowResumeRequest,
    WorkflowRunRequest,
    WorkflowUpdateRequest,
)

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])
chatflow_router = APIRouter(prefix="/api/v1/chatflows", tags=["chatflows"])
resource_router = APIRouter(prefix="/api/v1/workflow-resources", tags=["workflow-resources"])


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


def get_resource_registry(session: Session = Depends(get_session)) -> WorkflowResourceRegistry:
    return WorkflowResourceRegistry(
        mcp_repository=McpServerRepository(session),
        workflow_repository=WorkflowRepository(session),
        agent_repository=AgentRepository(session),
        api_resource_repository=ApiResourceRepository(session),
    )


def get_observe_service(session: Session = Depends(get_session)) -> ObserveService:
    return ObserveService(session)


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


@router.post("/{workflow_id}/runs")
def run_workflow(
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
    return success(build_composer_run_debug(detail, owner_type="WORKFLOW", owner_id=workflow_id))


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
    service: WorkflowService = Depends(get_chatflow_service),
) -> dict[str, Any]:
    return success(service.execute(chatflow_id, request))


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
    session_id = str(detail.get("sessionId") or "")
    session_state = chatflow_service.get_session_state(chatflow_id, session_id) if session_id else {}
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


@chatflow_router.delete("/{chatflow_id}")
def delete_chatflow(
    chatflow_id: int,
    service: WorkflowService = Depends(get_chatflow_service),
) -> dict[str, Any]:
    service.delete(chatflow_id)
    return success(None)
