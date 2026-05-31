from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.chat.domain.tool_schema import ToolDefinition
from app.modules.mcp.domain.client import FakeMcpClient, McpCallResult
from app.modules.mcp.domain.schema_builder import McpToolSchemaBuilder
from app.modules.mcp.infra.repository import McpServerRepository


class McpFacade:
    def __init__(self, session: Session) -> None:
        self._repository = McpServerRepository(session)
        self._client = FakeMcpClient()
        self._schema_builder = McpToolSchemaBuilder()

    def tool_names_for_servers(self, server_ids: list[int]) -> list[str]:
        return [tool.name for tool in self.tool_definitions_for_servers(server_ids)]

    def tool_definitions_for_servers(self, server_ids: list[int]) -> list[ToolDefinition]:
        definitions: list[ToolDefinition] = []
        for server_id in server_ids:
            row = self._repository.get(server_id)
            if row is None or not row["enabled"]:
                continue
            tools = self._client.list_tools(str(row["endpoint"]))
            schemas = self._schema_builder.build(tools)
            definitions.extend(
                ToolDefinition(
                    name=str(schema["name"]),
                    description=str(schema.get("description") or ""),
                    parameters=dict(schema.get("parameters") or {"type": "object", "properties": {}}),
                )
                for schema in schemas
            )
        return definitions

    def execute_tool_call(
        self,
        server_ids: list[int],
        tool_name: str,
        arguments: dict[str, object],
    ) -> McpCallResult:
        for server_id in server_ids:
            row = self._repository.get(server_id)
            if row is None or not row["enabled"]:
                continue
            endpoint = str(row["endpoint"])
            if tool_name not in {tool.name for tool in self._client.list_tools(endpoint)}:
                continue
            return self._client.call_tool(endpoint, tool_name, arguments)
        return McpCallResult(
            success=False,
            result=None,
            elapsed_ms=0,
            error_message=f"Tool is not bound to this agent: {tool_name}",
        )
