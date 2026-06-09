from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.responses import success
from app.modules.audit.infra.repository import AuditRepository
from app.modules.workflow.web.schemas import format_datetime

router = APIRouter(prefix="/api/v1/audit-records", tags=["audit-records"])


@router.get("")
def list_audit_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200, alias="pageSize"),
    action: str | None = None,
    resource_type: str | None = Query(None, alias="resourceType"),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    rows, total = AuditRepository(session).list_page(page, page_size, action, resource_type)
    return success({
        "list": [_audit_row(row) for row in rows],
        "total": total,
        "page": page,
        "pageSize": page_size,
    })


def _audit_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "actor": row["actor"],
        "action": row["action"],
        "resourceType": row["resource_type"],
        "resourceId": row["resource_id"],
        "status": row["status"],
        "metadata": row["metadata"] or {},
        "createdAt": format_datetime(row["created_at"]),
    }
