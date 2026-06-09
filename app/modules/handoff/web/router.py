from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.responses import success
from app.modules.audit.infra.repository import AuditRepository
from app.modules.handoff.domain.service import HandoffService
from app.modules.handoff.infra.repository import HandoffTicketRepository

router = APIRouter(prefix="/api/v1/handoffs", tags=["handoffs"])


def get_handoff_service(session: Session = Depends(get_session)) -> HandoffService:
    return HandoffService(HandoffTicketRepository(session), AuditRepository(session))


@router.get("")
def list_handoffs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    status: str | None = None,
    service: HandoffService = Depends(get_handoff_service),
) -> dict[str, Any]:
    return success(service.list(page, page_size, status))


@router.get("/{ticket_id}")
def get_handoff(
    ticket_id: int,
    service: HandoffService = Depends(get_handoff_service),
) -> dict[str, Any]:
    return success(service.get(ticket_id))


@router.post("/{ticket_id}/assign")
def assign_handoff(
    ticket_id: int,
    body: dict[str, Any],
    service: HandoffService = Depends(get_handoff_service),
) -> dict[str, Any]:
    return success(service.assign(ticket_id, str(body.get("assignee") or "")))


@router.post("/{ticket_id}/close")
def close_handoff(
    ticket_id: int,
    body: dict[str, Any] | None = None,
    service: HandoffService = Depends(get_handoff_service),
) -> dict[str, Any]:
    return success(service.close(ticket_id, str((body or {}).get("resolution") or "")))


@router.post("/{ticket_id}/return-to-bot")
def return_handoff_to_bot(
    ticket_id: int,
    service: HandoffService = Depends(get_handoff_service),
) -> dict[str, Any]:
    return success(service.return_to_bot(ticket_id))
