from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.responses import success
from app.modules.workflow.domain.api_resource_service import ApiResourceService
from app.modules.workflow.infra.api_resource_repository import ApiResourceRepository
from app.modules.workflow.web.api_resource_schemas import (
    ApiResourceCreateRequest,
    ApiResourceTestCallRequest,
    ApiResourceUpdateRequest,
    ApiToolCreateRequest,
)

router = APIRouter(prefix="/api/v1/api-resources", tags=["api-resources"])
tool_router = APIRouter(prefix="/api/v1/tools", tags=["tools"])


def get_api_resource_service(session: Session = Depends(get_session)) -> ApiResourceService:
    return ApiResourceService(ApiResourceRepository(session))


@router.get("")
def list_api_resources(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    enabled: bool | None = None,
    service: ApiResourceService = Depends(get_api_resource_service),
) -> dict[str, Any]:
    return success(service.list_resources(page, page_size, enabled))


@router.post("")
def create_api_resource(
    request: ApiResourceCreateRequest,
    service: ApiResourceService = Depends(get_api_resource_service),
) -> dict[str, Any]:
    return success(service.create_resource(request))


@router.get("/{resource_id}")
def get_api_resource(
    resource_id: int,
    service: ApiResourceService = Depends(get_api_resource_service),
) -> dict[str, Any]:
    return success(service.get_resource(resource_id))


@router.put("/{resource_id}")
def update_api_resource(
    resource_id: int,
    request: ApiResourceUpdateRequest,
    service: ApiResourceService = Depends(get_api_resource_service),
) -> dict[str, Any]:
    return success(service.update_resource(resource_id, request))


@router.post("/{resource_id}/test-call")
def test_api_resource_call(
    resource_id: int,
    request: ApiResourceTestCallRequest,
    service: ApiResourceService = Depends(get_api_resource_service),
) -> dict[str, Any]:
    return success(service.test_call(resource_id, request))


@router.delete("/{resource_id}")
def delete_api_resource(
    resource_id: int,
    service: ApiResourceService = Depends(get_api_resource_service),
) -> dict[str, Any]:
    service.delete_resource(resource_id)
    return success(None)


@tool_router.get("")
def list_tools(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    adapter_type: str | None = Query(None, alias="adapterType"),
    model_callable: bool | None = Query(None, alias="modelCallable"),
    enabled: bool | None = None,
    service: ApiResourceService = Depends(get_api_resource_service),
) -> dict[str, Any]:
    return success(service.list_tools(page, page_size, adapter_type, model_callable, enabled))


@tool_router.post("")
def create_tool(
    request: ApiToolCreateRequest,
    service: ApiResourceService = Depends(get_api_resource_service),
) -> dict[str, Any]:
    return success(service.create_tool(request))
