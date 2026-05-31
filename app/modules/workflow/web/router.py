from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.responses import success
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.infra.repository import WorkflowRepository
from app.modules.workflow.web.schemas import WorkflowCreateRequest, WorkflowRunRequest, WorkflowUpdateRequest

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])
chatflow_router = APIRouter(prefix="/api/v1/chatflows", tags=["chatflows"])


def get_workflow_service(session: Session = Depends(get_session)) -> WorkflowService:
    return WorkflowService(WorkflowRepository(session), flow_type="WORKFLOW")


def get_chatflow_service(session: Session = Depends(get_session)) -> WorkflowService:
    return WorkflowService(WorkflowRepository(session), flow_type="CHATFLOW")


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


@chatflow_router.delete("/{chatflow_id}")
def delete_chatflow(
    chatflow_id: int,
    service: WorkflowService = Depends(get_chatflow_service),
) -> dict[str, Any]:
    service.delete(chatflow_id)
    return success(None)
