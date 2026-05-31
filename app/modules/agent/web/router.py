from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.responses import success
from app.modules.agent.domain.service import AgentService
from app.modules.agent.infra.repository import AgentRepository
from app.modules.agent.web.schemas import (
    AgentCreateRequest,
    AgentToolBindingRequest,
    AgentUpdateRequest,
)
from app.modules.provider.api.facade import ProviderModelFacade

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


def get_agent_service(session: Session = Depends(get_session)) -> AgentService:
    return AgentService(AgentRepository(session), ProviderModelFacade(session))


@router.post("")
def create_agent(
    request: AgentCreateRequest,
    service: AgentService = Depends(get_agent_service),
) -> dict[str, Any]:
    return success(service.create(request))


@router.get("")
def list_agents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    enabled: bool | None = None,
    service: AgentService = Depends(get_agent_service),
) -> dict[str, Any]:
    return success(service.list_agents(page, page_size, enabled))


@router.get("/{agent_id}")
def get_agent(agent_id: int, service: AgentService = Depends(get_agent_service)) -> dict[str, Any]:
    return success(service.get(agent_id))


@router.put("/{agent_id}")
def update_agent(
    agent_id: int,
    request: AgentUpdateRequest,
    service: AgentService = Depends(get_agent_service),
) -> dict[str, Any]:
    return success(service.update(agent_id, request))


@router.delete("/{agent_id}")
def delete_agent(agent_id: int, service: AgentService = Depends(get_agent_service)) -> dict[str, Any]:
    service.delete(agent_id)
    return success(None)


@router.put("/{agent_id}/tools")
def replace_agent_tools(
    agent_id: int,
    request: AgentToolBindingRequest,
    service: AgentService = Depends(get_agent_service),
) -> dict[str, Any]:
    service.replace_tools(agent_id, request.tool_ids)
    return success(None)
