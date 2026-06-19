from __future__ import annotations

import socket

from sqlalchemy.orm import Session

from app.modules.agent.infra.repository import AgentRepository
from app.modules.knowledge.api.facade import KnowledgeFacade
from app.modules.mcp.api.facade import McpFacade
from app.modules.workflow.domain.runtime_job_worker import RuntimeJobWorker
from app.modules.workflow.domain.runtime_v2 import WorkflowRuntimeV2Service
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.infra.api_resource_repository import ApiResourceRepository
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.publish_repository import WorkflowPublishRepository
from app.modules.workflow.infra.realtime.redis_streams import RuntimeEventStreamBus
from app.modules.workflow.infra.repository import WorkflowRepository
from app.modules.workflow.infra.runtime_job_repository import RuntimeJobRepository
from app.modules.workflow.domain.api_resource_service import ApiResourceService
from app.modules.provider.api.facade import ProviderModelFacade


def default_runtime_job_worker_id(prefix: str = "runtime-worker") -> str:
    return f"{prefix}-{socket.gethostname()}"


def build_workflow_runtime_job_worker(
    session: Session,
    *,
    worker_id: str | None = None,
    lease_seconds: int = 300,
    event_stream_bus: RuntimeEventStreamBus | None = None,
) -> RuntimeJobWorker:
    return RuntimeJobWorker(
        job_repository=RuntimeJobRepository(session),
        complete_run=lambda run_id: complete_workflow_runtime_job(
            session,
            run_id,
            event_stream_bus=event_stream_bus,
        ),
        worker_id=worker_id or default_runtime_job_worker_id(),
        lease_seconds=lease_seconds,
    )


def complete_workflow_runtime_job(
    session: Session,
    run_id: int,
    *,
    event_stream_bus: RuntimeEventStreamBus | None = None,
) -> None:
    llm_service = _workflow_llm_service(session)
    WorkflowRuntimeV2Service(
        WorkflowRepository(session),
        ChatflowStateRepository(session, event_stream_bus=event_stream_bus),
        WorkflowPublishRepository(session),
        knowledge_facade=KnowledgeFacade(session),
        llm_completer_resolver=llm_service.runtime_v2_llm_completer,
        agent_invoker_resolver=llm_service.runtime_v2_agent_invoker,
        mcp_tool_executor=llm_service.runtime_v2_mcp_tool_executor(),
        api_tool_executor=llm_service.runtime_v2_api_tool_executor(),
    ).complete_run(run_id)


def _workflow_llm_service(session: Session) -> WorkflowService:
    return WorkflowService(
        WorkflowRepository(session),
        flow_type="WORKFLOW",
        agent_repository=AgentRepository(session),
        model_facade=ProviderModelFacade(session),
        knowledge_facade=KnowledgeFacade(session),
        mcp_tool_executor=McpFacade(session),
        api_tool_executor=ApiResourceService(ApiResourceRepository(session)),
    )
