from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.responses import success
from app.modules.mcp.domain.service import McpServerService
from app.modules.mcp.infra.repository import McpServerRepository
from app.modules.mcp.web.schemas import McpDebugRequest, McpServerCreateRequest, McpServerUpdateRequest

router = APIRouter(prefix="/api/v1/mcp-servers", tags=["mcp-servers"])


def get_mcp_server_service(session: Session = Depends(get_session)) -> McpServerService:
    return McpServerService(McpServerRepository(session))


@router.get("")
def list_mcp_servers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    enabled: bool | None = None,
    service: McpServerService = Depends(get_mcp_server_service),
) -> dict[str, Any]:
    return success(service.list(page, page_size, enabled))


@router.post("")
def create_mcp_server(
    request: McpServerCreateRequest,
    service: McpServerService = Depends(get_mcp_server_service),
) -> dict[str, Any]:
    return success(service.create(request))


@router.get("/{server_id}")
def get_mcp_server(
    server_id: int,
    service: McpServerService = Depends(get_mcp_server_service),
) -> dict[str, Any]:
    return success(service.get(server_id))


@router.put("/{server_id}")
def update_mcp_server(
    server_id: int,
    request: McpServerUpdateRequest,
    service: McpServerService = Depends(get_mcp_server_service),
) -> dict[str, Any]:
    return success(service.update(server_id, request))


@router.post("/{server_id}/test")
def test_mcp_server(
    server_id: int,
    service: McpServerService = Depends(get_mcp_server_service),
) -> dict[str, Any]:
    return success(service.test_connection(server_id))


@router.get("/{server_id}/tools")
def list_mcp_tools(
    server_id: int,
    service: McpServerService = Depends(get_mcp_server_service),
) -> dict[str, Any]:
    return success(service.list_tools(server_id))


@router.post("/{server_id}/debug")
def debug_mcp_tool(
    server_id: int,
    request: McpDebugRequest,
    service: McpServerService = Depends(get_mcp_server_service),
) -> dict[str, Any]:
    return success(service.debug_tool(server_id, request))


@router.delete("/{server_id}")
def delete_mcp_server(
    server_id: int,
    service: McpServerService = Depends(get_mcp_server_service),
) -> dict[str, Any]:
    service.delete(server_id)
    return success(None)
