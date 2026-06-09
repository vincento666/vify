from __future__ import annotations

from typing import Any

from app.modules.agent.infra.repository import AgentRepository
from app.modules.mcp.domain.client import FakeMcpClient, McpToolDetail
from app.modules.mcp.infra.repository import McpServerRepository
from app.modules.workflow.infra.api_resource_repository import ApiResourceRepository
from app.modules.workflow.infra.repository import WorkflowRepository


class WorkflowResourceRegistry:
    def __init__(
        self,
        mcp_repository: McpServerRepository,
        workflow_repository: WorkflowRepository,
        agent_repository: AgentRepository | None = None,
        api_resource_repository: ApiResourceRepository | None = None,
        mcp_client: FakeMcpClient | None = None,
    ) -> None:
        self._mcp_repository = mcp_repository
        self._workflow_repository = workflow_repository
        self._agent_repository = agent_repository
        self._api_resource_repository = api_resource_repository
        self._mcp_client = mcp_client or FakeMcpClient()

    def list_resources(self, flow_type: str = "WORKFLOW", resource_type: str | None = None) -> dict[str, Any]:
        resources = [
            *self._api_tool_resources(flow_type),
            *self._mcp_resources(flow_type),
            *self._workflow_resources(flow_type),
            *self._agent_resources(flow_type),
        ]
        if resource_type:
            normalized = str(resource_type).strip().upper().replace("-", "_")
            resources = [resource for resource in resources if str(resource.get("resourceType") or "").upper() == normalized]
        return {"list": resources, "total": len(resources)}

    def _api_tool_resources(self, flow_type: str) -> list[dict[str, Any]]:
        if self._api_resource_repository is None:
            return []
        rows, _total = self._api_resource_repository.list_tools(1, 200, adapter_type="API_RESOURCE")
        resources: list[dict[str, Any]] = []
        for row in rows:
            enabled = bool(row.get("enabled"))
            resources.append(
                _resource(
                    resource_id=f"api-tool:{int(row['id'])}:{row['name']}",
                    resource_type="API_TOOL",
                    display_name=str(row.get("display_name") or row["name"]),
                    description=str(row.get("description") or ""),
                    enabled=enabled,
                    credential_status="PRESENT",
                    runtime_status="READY" if enabled else "DISABLED",
                    health_status="UP" if enabled else "UNKNOWN",
                    disabled_reason="" if enabled else "Tool disabled by admin",
                    input_schema=row.get("input_schema") or {"type": "object", "properties": {}},
                    output_schema=row.get("output_schema") or {"type": "object", "properties": {"result": {"type": "string"}}},
                    capabilities=["api", "tool", "model-callable"] if bool(row.get("model_callable")) else ["api", "tool"],
                    flow_type=flow_type,
                    metadata={
                        "toolId": int(row["id"]),
                        "toolName": str(row["name"]),
                        "apiResourceId": int(row["api_resource_id"]) if row.get("api_resource_id") is not None else None,
                        "modelCallable": bool(row.get("model_callable")),
                    },
                )
            )
        return resources

    def _mcp_resources(self, flow_type: str) -> list[dict[str, Any]]:
        rows, _total = self._mcp_repository.list_page(1, 200)
        resources: list[dict[str, Any]] = []
        for row in rows:
            server_id = int(row["id"])
            endpoint = str(row["endpoint"])
            display_name = str(row["name"])
            if not bool(row["enabled"]):
                resources.append(
                    _resource(
                        resource_id=f"mcp:{server_id}",
                        resource_type="MCP_TOOL",
                        display_name=display_name,
                        description=str(row.get("description") or ""),
                        enabled=False,
                        credential_status="PRESENT",
                        runtime_status="DISABLED",
                        health_status="UNKNOWN",
                        disabled_reason="Resource disabled by admin",
                        flow_type=flow_type,
                    )
                )
                continue
            if _missing_credential(endpoint):
                resources.append(
                    _resource(
                        resource_id=f"mcp:{server_id}",
                        resource_type="MCP_TOOL",
                        display_name=display_name,
                        description=str(row.get("description") or ""),
                        enabled=False,
                        credential_status="MISSING",
                        runtime_status="CREDENTIAL_MISSING",
                        health_status="UNKNOWN",
                        disabled_reason="Missing credential for resource",
                        flow_type=flow_type,
                    )
                )
                continue
            connection = self._mcp_client.test_connection(endpoint)
            if not connection.success:
                resources.append(
                    _resource(
                        resource_id=f"mcp:{server_id}",
                        resource_type="MCP_TOOL",
                        display_name=display_name,
                        description=str(row.get("description") or ""),
                        enabled=False,
                        credential_status="PRESENT",
                        runtime_status="UNHEALTHY",
                        health_status="DOWN",
                        disabled_reason=connection.error_message or "Resource health check failed",
                        flow_type=flow_type,
                    )
                )
                continue
            tools = self._mcp_client.list_tools(endpoint)
            if not tools:
                resources.append(
                    _resource(
                        resource_id=f"mcp:{server_id}",
                        resource_type="MCP_TOOL",
                        display_name=display_name,
                        description=str(row.get("description") or ""),
                        enabled=False,
                        credential_status="PRESENT",
                        runtime_status="SCHEMA_MISSING",
                        health_status="UP",
                        disabled_reason="No callable tool schema found",
                        flow_type=flow_type,
                    )
                )
                continue
            resources.extend(self._tool_resource(server_id, row, tool, flow_type) for tool in tools)
        return resources

    def _tool_resource(
        self,
        server_id: int,
        row: dict[str, Any],
        tool: McpToolDetail,
        flow_type: str,
    ) -> dict[str, Any]:
        write_capable = tool.name.startswith(("refund_", "create_", "update_", "delete_"))
        return _resource(
            resource_id=f"mcp:{server_id}:{tool.name}",
            resource_type="MCP_TOOL",
            display_name=tool.name,
            description=tool.description,
            enabled=True,
            credential_status="PRESENT",
            runtime_status="READY",
            health_status="UP",
            disabled_reason="",
            input_schema=tool.input_schema or {"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
            capabilities=["write" if write_capable else "read"],
            flow_type=flow_type,
            metadata={"serverId": server_id, "serverName": str(row["name"])},
        )

    def _workflow_resources(self, flow_type: str) -> list[dict[str, Any]]:
        rows, _total = self._workflow_repository.list_page(1, 200, flow_type="WORKFLOW")
        resources: list[dict[str, Any]] = []
        for row in rows:
            status = str(row["status"])
            enabled = status == "PUBLISHED"
            resources.append(
                _resource(
                    resource_id=f"workflow:{int(row['id'])}",
                    resource_type="SUBWORKFLOW",
                    display_name=str(row["name"]),
                    description=str(row.get("description") or ""),
                    enabled=enabled,
                    credential_status="PRESENT",
                    runtime_status="READY" if enabled else "NOT_PUBLISHED",
                    health_status="UP" if enabled else "UNKNOWN",
                    disabled_reason="" if enabled else "Workflow must be published before it can be invoked",
                    input_schema={"type": "object", "properties": {}},
                    output_schema={"type": "object", "properties": {"output": {"type": "string"}}},
                    capabilities=["subworkflow"],
                    flow_type=flow_type,
                    metadata={"workflowId": int(row["id"]), "status": status},
                )
            )
        return resources

    def _agent_resources(self, flow_type: str) -> list[dict[str, Any]]:
        if self._agent_repository is None:
            return []
        rows, _total = self._agent_repository.list_page(1, 200)
        resources: list[dict[str, Any]] = []
        for row in rows:
            enabled = bool(row.get("enabled")) and row.get("workflow_id") is None
            resources.append(
                _resource(
                    resource_id=f"agent:{int(row['id'])}",
                    resource_type="AGENT",
                    display_name=str(row["name"]),
                    description=str(row.get("description") or ""),
                    enabled=enabled,
                    credential_status="PRESENT",
                    runtime_status="READY" if enabled else "UNAVAILABLE",
                    health_status="UP" if enabled else "UNKNOWN",
                    disabled_reason="" if enabled else "Agent must be enabled and not bound to a workflow",
                    input_schema={"type": "object", "properties": {"message": {"type": "string"}}},
                    output_schema={"type": "object", "properties": {"answer": {"type": "string"}}},
                    capabilities=["agent"],
                    flow_type=flow_type,
                    metadata={"agentId": int(row["id"]), "modelConfigId": int(row["model_config_id"])},
                )
            )
        return resources


def _resource(
    *,
    resource_id: str,
    resource_type: str,
    display_name: str,
    description: str,
    enabled: bool,
    credential_status: str,
    runtime_status: str,
    health_status: str,
    disabled_reason: str,
    flow_type: str,
    input_schema: dict[str, Any] | None = None,
    output_schema: dict[str, Any] | None = None,
    capabilities: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "resourceId": resource_id,
        "resourceType": resource_type,
        "displayName": display_name,
        "description": description,
        "enabled": enabled,
        "inputSchema": input_schema or {"type": "object", "properties": {}},
        "outputSchema": output_schema or {"type": "object", "properties": {}},
        "capabilities": capabilities or [],
        "flowTypeSupport": ["WORKFLOW", "CHATFLOW"],
        "credentialStatus": credential_status,
        "runtimeStatus": runtime_status,
        "healthStatus": health_status,
        "disabledReason": disabled_reason,
        "metadata": metadata or {},
    }


def _missing_credential(endpoint: str) -> bool:
    lowered = endpoint.lower()
    return "credential=missing" in lowered or "missing-credential" in lowered
