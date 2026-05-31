from __future__ import annotations

from typing import Any

from app.core.errors import BizError, ErrorCode
from app.modules.agent.infra.repository import AgentRepository
from app.modules.agent.web.schemas import AgentCreateRequest, AgentListPage, AgentUpdateRequest
from app.modules.provider.api.facade import ProviderModelFacade


class AgentService:
    def __init__(self, repository: AgentRepository, model_facade: ProviderModelFacade) -> None:
        self._repository = repository
        self._model_facade = model_facade

    def create(self, request: AgentCreateRequest) -> dict[str, Any]:
        self._validate_model(request.model_config_id)
        tool_ids = self._dedupe_tool_ids(request.tool_ids)
        self._validate_tool_ids(tool_ids)
        row = self._repository.create(self._values_from_create(request))
        self._repository.replace_tool_bindings(int(row["id"]), tool_ids)
        return self._detail(row)

    def list_agents(self, page: int, page_size: int, enabled: bool | None) -> dict[str, Any]:
        rows, total = self._repository.list_page(page, page_size, enabled)
        response = AgentListPage(
            list=[self._list_item(row) for row in rows],
            total=total,
            page=page,
            pageSize=page_size,
        )
        return response.model_dump(by_alias=True)

    def get(self, agent_id: int) -> dict[str, Any]:
        row = self._repository.get(agent_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Agent not found")
        return self._detail(row)

    def update(self, agent_id: int, request: AgentUpdateRequest) -> dict[str, Any]:
        self._validate_model(request.model_config_id)
        row = self._repository.update(agent_id, self._values_from_update(request))
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Agent not found")
        return self._detail(row)

    def delete(self, agent_id: int) -> None:
        if not self._repository.delete(agent_id):
            raise BizError(ErrorCode.NOT_FOUND, "Agent not found")

    def replace_tools(self, agent_id: int, tool_ids: list[int]) -> None:
        self.get(agent_id)
        deduped_tool_ids = self._dedupe_tool_ids(tool_ids)
        self._validate_tool_ids(deduped_tool_ids)
        self._repository.replace_tool_bindings(agent_id, deduped_tool_ids)

    def _values_from_create(self, request: AgentCreateRequest) -> dict[str, Any]:
        return {
            "name": request.name,
            "description": request.description,
            "system_prompt": request.system_prompt,
            "model_config_id": request.model_config_id,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "max_context_turns": request.max_context_turns,
            "knowledge_base_id": request.knowledge_base_id,
            "workflow_id": request.workflow_id,
        }

    def _validate_model(self, model_config_id: int) -> None:
        self._model_facade.get_enabled_model_config(model_config_id)

    def _dedupe_tool_ids(self, tool_ids: list[int]) -> list[int]:
        seen: set[int] = set()
        deduped: list[int] = []
        for tool_id in tool_ids:
            if tool_id in seen:
                continue
            seen.add(tool_id)
            deduped.append(tool_id)
        return deduped

    def _validate_tool_ids(self, tool_ids: list[int]) -> None:
        if not tool_ids:
            return
        available = set(self._repository.list_available_tool_ids(tool_ids))
        missing = [tool_id for tool_id in tool_ids if tool_id not in available]
        if missing:
            raise BizError(ErrorCode.VALIDATION_ERROR, f"MCP server not available: {missing[0]}")

    def _values_from_update(self, request: AgentUpdateRequest) -> dict[str, Any]:
        return {
            "name": request.name,
            "description": request.description,
            "system_prompt": request.system_prompt,
            "model_config_id": request.model_config_id,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "max_context_turns": request.max_context_turns,
            "knowledge_base_id": request.knowledge_base_id,
            "workflow_id": request.workflow_id,
        }

    def _detail(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "name": row["name"],
            "description": row["description"] or "",
            "systemPrompt": row["system_prompt"] or "",
            "modelConfigId": int(row["model_config_id"]),
            "temperature": float(row["temperature"]),
            "maxTokens": int(row["max_tokens"]),
            "maxContextTurns": int(row["max_context_turns"]),
            "enabled": 1 if row["enabled"] else 0,
            "toolIds": self._repository.list_tool_ids(int(row["id"])),
            "knowledgeBaseId": row.get("knowledge_base_id"),
            "workflowId": row.get("workflow_id"),
            "createdAt": row["created_at"].isoformat(),
            "updatedAt": row["updated_at"].isoformat(),
        }

    def _list_item(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "name": row["name"],
            "description": row["description"] or "",
            "modelConfigId": int(row["model_config_id"]),
            "temperature": float(row["temperature"]),
            "enabled": 1 if row["enabled"] else 0,
            "toolCount": self._repository.tool_count(int(row["id"])),
            "workflowId": row.get("workflow_id"),
            "knowledgeBaseId": row.get("knowledge_base_id"),
            "createdAt": row["created_at"].isoformat(),
        }
