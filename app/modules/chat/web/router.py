from collections.abc import AsyncIterable, Iterable
from typing import Any

import anyio
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_session, get_session_factory
from app.core.responses import success
from app.modules.chat.domain.service import ChatService
from app.modules.chat.infra.repository import ChatRepository
from app.modules.chat.web.schemas import ChatMessageCreateRequest, ChatSessionCreateRequest
from app.modules.knowledge.api.facade import KnowledgeFacade
from app.modules.mcp.api.facade import McpFacade
from app.modules.workflow.api.facade import WorkflowFacade

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


def get_chat_service(session: Session = Depends(get_session)) -> ChatService:
    return ChatService(
        ChatRepository(session),
        knowledge_facade=KnowledgeFacade(session),
        workflow_facade=WorkflowFacade(session),
        mcp_facade=McpFacade(session),
    )


@router.post("/sessions")
def create_session(
    request: ChatSessionCreateRequest,
    service: ChatService = Depends(get_chat_service),
) -> dict[str, Any]:
    return success(service.create_session(request))


@router.get("/sessions")
def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    agent_id: int | None = Query(None, alias="agentId"),
    service: ChatService = Depends(get_chat_service),
) -> dict[str, Any]:
    return success(service.list_sessions(page, page_size, agent_id))


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    service: ChatService = Depends(get_chat_service),
) -> dict[str, Any]:
    service.delete_session(session_id)
    return success(None)


@router.get("/sessions/{session_id}/messages")
def list_messages(
    session_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    service: ChatService = Depends(get_chat_service),
) -> dict[str, Any]:
    return success(service.list_messages(session_id, page, page_size))


@router.post("/sessions/{session_id}/messages", response_model=None)
def send_message(
    session_id: int,
    request: ChatMessageCreateRequest,
) -> Any:
    with get_session_factory()() as session:
        service = ChatService(
            ChatRepository(session),
            knowledge_facade=KnowledgeFacade(session),
            workflow_facade=WorkflowFacade(session),
            mcp_facade=McpFacade(session),
        )
        if not request.stream:
            return success(service.send_message(session_id, request))
        events = service.stream_message_events(session_id, request)
    return StreamingResponse(_iter_events(events), media_type="text/event-stream")


async def _iter_events(events: Iterable[str]) -> AsyncIterable[str]:
    for event in events:
        yield event
        await anyio.sleep(0.01)
