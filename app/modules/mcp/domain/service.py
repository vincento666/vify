from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.core.errors import BizError, ErrorCode
from app.modules.mcp.domain.client import FakeMcpClient, McpCallResult, McpConnectionResult, McpToolDetail
from app.modules.mcp.infra.repository import McpServerRepository
from app.modules.mcp.web.schemas import (
    McpDebugRequest,
    McpDebugResultResponse,
    McpServerCreateRequest,
    McpServerPageResponse,
    McpServerResponse,
    McpServerUpdateRequest,
    McpTestResultResponse,
    McpToolDetailResponse,
    format_datetime,
)


class McpServerService:
    def __init__(self, repository: McpServerRepository, client: FakeMcpClient | None = None) -> None:
        self._repository = repository
        self._client = client or FakeMcpClient()

    def list(self, page: int, page_size: int, enabled: bool | None) -> dict[str, Any]:
        rows, total = self._repository.list_page(page, page_size, enabled)
        response = McpServerPageResponse(
            list=[self._response(row) for row in rows],
            total=total,
            page=page,
            pageSize=page_size,
        )
        return response.model_dump(by_alias=True)

    def create(self, request: McpServerCreateRequest) -> dict[str, Any]:
        row = self._repository.create(
            {
                "name": request.name,
                "endpoint": request.endpoint,
                "description": request.description,
            }
        )
        return self._response(row).model_dump(by_alias=True)

    def get(self, server_id: int) -> dict[str, Any]:
        row = self._repository.get(server_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "MCP server not found")
        return self._response(row).model_dump(by_alias=True)

    def update(self, server_id: int, request: McpServerUpdateRequest) -> dict[str, Any]:
        values: dict[str, Any] = {}
        if request.name is not None:
            values["name"] = request.name
        if request.endpoint is not None:
            values["endpoint"] = request.endpoint
        if request.description is not None:
            values["description"] = request.description
        if request.enabled is not None:
            values["enabled"] = bool(request.enabled)
        row = self._repository.update(server_id, values)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "MCP server not found")
        return self._response(row).model_dump(by_alias=True)

    def delete(self, server_id: int) -> None:
        if not self._repository.delete(server_id):
            raise BizError(ErrorCode.NOT_FOUND, "MCP server not found")

    def test_connection(self, server_id: int) -> dict[str, Any]:
        row = self._repository.get(server_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "MCP server not found")
        return self._test_response(self._client.test_connection(str(row["endpoint"]))).model_dump(by_alias=True)

    def list_tools(self, server_id: int) -> Sequence[dict[str, Any]]:
        row = self._repository.get(server_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "MCP server not found")
        return [self._tool_response(tool).model_dump(by_alias=True) for tool in self._client.list_tools(str(row["endpoint"]))]

    def debug_tool(self, server_id: int, request: McpDebugRequest) -> dict[str, Any]:
        row = self._repository.get(server_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "MCP server not found")
        result = self._client.call_tool(str(row["endpoint"]), request.tool_name, request.arguments)
        return self._debug_response(result).model_dump(by_alias=True)

    def _response(self, row: dict[str, Any]) -> McpServerResponse:
        return McpServerResponse(
            id=int(row["id"]),
            name=row["name"],
            endpoint=row["endpoint"],
            description=row["description"] or "",
            enabled=1 if row["enabled"] else 0,
            createdAt=format_datetime(row["created_at"]),
            updatedAt=format_datetime(row["updated_at"]),
            tools=[],
        )

    def _test_response(self, result: McpConnectionResult) -> McpTestResultResponse:
        return McpTestResultResponse(
            success=result.success,
            latencyMs=result.latency_ms,
            tools=result.tools,
            errorMessage=result.error_message,
        )

    def _tool_response(self, tool: McpToolDetail) -> McpToolDetailResponse:
        return McpToolDetailResponse(
            name=tool.name,
            description=tool.description,
            inputSchema=tool.input_schema,
            requiredParams=tool.required_params,
        )

    def _debug_response(self, result: McpCallResult) -> McpDebugResultResponse:
        return McpDebugResultResponse(
            success=result.success,
            result=result.result,
            elapsedMs=result.elapsed_ms,
            errorMessage=result.error_message,
        )
