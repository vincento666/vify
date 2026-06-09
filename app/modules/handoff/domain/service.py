from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.core.errors import BizError, ErrorCode
from app.core.sanitization import sanitize_value
from app.modules.audit.infra.repository import AuditRepository
from app.modules.handoff.infra.repository import HandoffTicketRepository
from app.modules.workflow.web.schemas import format_datetime


class HandoffService:
    def __init__(self, repository: HandoffTicketRepository, audit_repository: AuditRepository | None = None) -> None:
        self._repository = repository
        self._audit_repository = audit_repository

    def create_ticket(self, data: dict[str, Any]) -> dict[str, Any]:
        sla_minutes = _positive_int(data.get("sla_minutes"), default=30)
        row = self._repository.create(
            {
                **data,
                "status": data.get("status") or "queued",
                "sla_due_at": datetime.now() + timedelta(minutes=sla_minutes),
                "transcript_snapshot": sanitize_value(data.get("transcript_snapshot") or []),
                "context_snapshot": sanitize_value(data.get("context_snapshot") or {}),
            }
        )
        return self._response(row)

    def list(self, page: int, page_size: int, status: str | None = None) -> dict[str, Any]:
        rows, total = self._repository.list_page(page, page_size, status)
        return {"list": [self._response(row) for row in rows], "total": total, "page": page, "pageSize": page_size}

    def get(self, ticket_id: int) -> dict[str, Any]:
        row = self._repository.get(ticket_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Handoff ticket not found")
        return self._response(row)

    def assign(self, ticket_id: int, assignee: str) -> dict[str, Any]:
        row = self._update_or_404(ticket_id, {"assignee": assignee.strip(), "status": "assigned"})
        self._audit("HANDOFF_ASSIGN", ticket_id, {"assignee": assignee.strip()})
        return self._response(row)

    def close(self, ticket_id: int, resolution: str = "") -> dict[str, Any]:
        row = self._update_or_404(ticket_id, {"status": "closed", "closed_at": datetime.now()})
        self._audit("HANDOFF_CLOSE", ticket_id, {"resolution": resolution})
        return self._response(row)

    def return_to_bot(self, ticket_id: int) -> dict[str, Any]:
        row = self._update_or_404(ticket_id, {"status": "returned_to_bot", "closed_at": datetime.now()})
        self._audit("HANDOFF_RETURN_TO_BOT", ticket_id, {})
        return self._response(row)

    def _update_or_404(self, ticket_id: int, values: dict[str, Any]) -> dict[str, Any]:
        row = self._repository.update(ticket_id, values)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Handoff ticket not found")
        return row

    def _response(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "sessionId": row["session_id"],
            "conversationId": row["conversation_id"],
            "userId": row["user_id"],
            "channel": row["channel"],
            "queue": row["queue"],
            "assignee": row["assignee"],
            "status": row["status"],
            "reason": row["reason"],
            "priority": row["priority"],
            "slaDueAt": format_datetime(row["sla_due_at"]) if row.get("sla_due_at") else None,
            "slaState": _sla_state(row.get("sla_due_at"), row["status"]),
            "transcriptSnapshot": sanitize_value(row["transcript_snapshot"] or []),
            "contextSnapshot": sanitize_value(row["context_snapshot"] or {}),
            "createdAt": format_datetime(row["created_at"]),
            "updatedAt": format_datetime(row["updated_at"]),
            "closedAt": format_datetime(row["closed_at"]) if row.get("closed_at") else None,
        }

    def _audit(self, action: str, ticket_id: int, metadata: dict[str, Any]) -> None:
        if self._audit_repository is None:
            return
        self._audit_repository.record(
            action=action,
            resource_type="HANDOFF",
            resource_id=ticket_id,
            status="succeeded",
            metadata=metadata,
        )


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _sla_state(due_at: Any, status: str) -> str:
    if due_at is None or status in {"closed", "resolved", "returned_to_bot"}:
        return "none"
    now = datetime.now()
    if due_at <= now:
        return "overdue"
    if due_at <= now + timedelta(minutes=5):
        return "warning"
    return "healthy"
