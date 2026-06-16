from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.errors import BizError, ErrorCode
from app.core.host.context import RequestContext
from app.core.host.dependencies import get_request_context
from app.core.responses import success
from app.modules.audit.infra.repository import AuditRepository
from app.modules.agent.domain.service import AgentService
from app.modules.agent.infra.repository import AgentRepository
from app.modules.agent.web.schemas import (
    AgentCreateRequest,
    AgentPublishCreateRequest,
    AgentPromptOptimizationRequest,
    AgentToolBindingRequest,
    AgentUpdateRequest,
    AgentVersionCreateRequest,
)
from app.modules.chat.infra.repository import ChatRepository
from app.modules.provider.api.facade import ProviderModelFacade

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


def get_agent_service(
    session: Session = Depends(get_session),
    request_context: RequestContext = Depends(get_request_context),
) -> AgentService:
    return AgentService(
        AgentRepository(session),
        ProviderModelFacade(session),
        AuditRepository(session),
        request_context,
    )


def get_chat_repository(session: Session = Depends(get_session)) -> ChatRepository:
    return ChatRepository(session)


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


@router.get("/{agent_id}/versions")
def list_agent_versions(agent_id: int, service: AgentService = Depends(get_agent_service)) -> dict[str, Any]:
    return success(service.list_versions(agent_id))


@router.post("/{agent_id}/versions")
def create_agent_version(
    agent_id: int,
    request: AgentVersionCreateRequest,
    service: AgentService = Depends(get_agent_service),
) -> dict[str, Any]:
    return success(service.create_version(agent_id, request))


@router.put("/{agent_id}/versions/{version_id}/release")
def release_agent_version(
    agent_id: int,
    version_id: int,
    service: AgentService = Depends(get_agent_service),
) -> dict[str, Any]:
    return success(service.release_version(agent_id, version_id))


@router.get("/{agent_id}/publishes")
def list_agent_publishes(agent_id: int, service: AgentService = Depends(get_agent_service)) -> dict[str, Any]:
    return success(service.list_publishes(agent_id))


@router.post("/{agent_id}/publishes")
def publish_agent(
    agent_id: int,
    request: AgentPublishCreateRequest,
    service: AgentService = Depends(get_agent_service),
) -> dict[str, Any]:
    return success(service.publish(agent_id, request))


@router.put("/{agent_id}/publishes/{publish_id}/unpublish")
def unpublish_agent(
    agent_id: int,
    publish_id: int,
    service: AgentService = Depends(get_agent_service),
) -> dict[str, Any]:
    return success(service.unpublish(agent_id, publish_id))


@router.get("/{agent_id}/prompt-optimizations")
def list_prompt_optimizations(agent_id: int, service: AgentService = Depends(get_agent_service)) -> dict[str, Any]:
    return success(service.list_prompt_optimizations(agent_id))


@router.post("/{agent_id}/prompt-optimizations")
def optimize_prompt(
    agent_id: int,
    request: AgentPromptOptimizationRequest,
    service: AgentService = Depends(get_agent_service),
) -> dict[str, Any]:
    return success(service.optimize_prompt(agent_id, request))


@router.get("/{agent_id}/preview-runs/{preview_run_id}/debug")
def get_agent_preview_run_debug(
    agent_id: int,
    preview_run_id: int,
    chat_repository: ChatRepository = Depends(get_chat_repository),
) -> dict[str, Any]:
    chat_session = chat_repository.get_session(preview_run_id)
    if chat_session is None or int(chat_session["agent_id"]) != agent_id:
        raise BizError(ErrorCode.NOT_FOUND, "Agent preview run not found")
    agent = chat_repository.get_agent(agent_id)
    if agent is None:
        raise BizError(ErrorCode.NOT_FOUND, "Agent not found")
    messages, _total = chat_repository.list_messages(preview_run_id, 1, 100)
    user_message = next((message for message in reversed(messages) if message["role"] == "user"), None)
    assistant_message = next((message for message in reversed(messages) if message["role"] == "assistant"), None)
    if user_message is None or assistant_message is None:
        raise BizError(ErrorCode.NOT_FOUND, "Agent preview run has no completed turn")
    return success(_agent_preview_debug_response(agent, chat_session, user_message, assistant_message))


def _agent_preview_debug_response(
    agent: dict[str, Any],
    chat_session: dict[str, Any],
    user_message: dict[str, Any],
    assistant_message: dict[str, Any],
) -> dict[str, Any]:
    started_at = user_message["created_at"]
    completed_at = assistant_message["created_at"]
    elapsed_ms = max(0, int((completed_at - started_at).total_seconds() * 1000))
    latency_ms = int(assistant_message.get("latency_ms") or elapsed_ms)
    first_response_ms = latency_ms if latency_ms > 0 else elapsed_ms
    llm_offset = max(8, min(92, round((first_response_ms / elapsed_ms) * 100))) if elapsed_ms else 8
    llm_width = max(8, 100 - llm_offset)
    tool_calls = assistant_message.get("tool_calls") if isinstance(assistant_message.get("tool_calls"), list) else []
    tool_nodes = [
        {
            "id": f"tool:{tool_call.get('toolName') or 'unknown'}",
            "depth": 2,
            "active": False,
            "icon": "◇",
            "label": f"调用工具 {tool_call.get('toolName') or 'unknown'}",
            "detail": str(tool_call.get("status") or ""),
        }
        for tool_call in tool_calls
    ]
    tool_lanes = _debug_tool_lanes(tool_calls)
    return {
        "previewRunId": int(chat_session["id"]),
        "agentId": int(agent["id"]),
        "sessionId": int(chat_session["id"]),
        "status": "失败" if assistant_message.get("finish_reason") == "error" else "成功",
        "finishReason": assistant_message.get("finish_reason") or "stop",
        "elapsedMs": elapsed_ms,
        "firstResponseMs": first_response_ms,
        "latencyMs": latency_ms,
        "inputChars": len(str(user_message.get("content") or "")),
        "outputChars": len(str(assistant_message.get("content") or "")),
        "startedAt": started_at.isoformat(),
        "input": {"content": user_message.get("content") or "", "messageId": int(user_message["id"])},
        "output": {"content": assistant_message.get("content") or "", "messageId": int(assistant_message["id"])},
        "toolCalls": tool_calls,
        "nodes": [
            {"id": "user", "depth": 0, "active": True, "icon": "↪", "label": "用户输入", "detail": "UserInput"},
            {"id": "llm", "depth": 1, "active": False, "icon": "●", "label": "调用 LLM", "detail": str(agent.get("model_config_id") or "")},
            *tool_nodes,
        ],
        "axisTicks": _debug_axis_ticks(elapsed_ms),
        "flameLanes": [
            {"id": "user", "label": "用户输入 UserInput", "offsetPct": 0, "widthPct": llm_offset},
            {"id": "llm", "label": "调用 LLM Agent Model", "offsetPct": llm_offset, "widthPct": llm_width},
            *tool_lanes,
        ],
    }


def _debug_axis_ticks(elapsed_ms: int) -> list[int]:
    max_ms = max(1000, ((elapsed_ms + 999) // 1000) * 1000)
    step = max(200, ((max_ms // 5 + 99) // 100) * 100)
    return [step * (index + 1) for index in range(5)]


def _debug_tool_lanes(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lanes: list[dict[str, Any]] = []
    offset = 62
    for index, tool_call in enumerate(tool_calls):
        name = str(tool_call.get("toolName") or "unknown")
        status = str(tool_call.get("status") or "")
        lanes.append(
            {
                "id": f"tool:{name}:{index}",
                "label": f"调用工具 {name} · {status}",
                "offsetPct": min(92, offset + index * 6),
                "widthPct": max(8, min(30, int(tool_call.get("latencyMs") or 1) + 8)),
            }
        )
    return lanes
