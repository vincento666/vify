from __future__ import annotations

from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.schema import register_baseline_tables

register_baseline_tables()


class HandoffTicketRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._ticket = Base.metadata.tables["handoff_ticket"]

    def create(self, values: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now()
        result = self._session.execute(
            self._ticket.insert()
            .values(
                session_id=values["session_id"],
                conversation_id=values.get("conversation_id") or "",
                user_id=values.get("user_id") or "",
                channel=values.get("channel") or "web",
                queue=values.get("queue") or "general",
                assignee=values.get("assignee") or "",
                status=values.get("status") or "queued",
                reason=values.get("reason") or "",
                priority=values.get("priority") or "normal",
                sla_due_at=values.get("sla_due_at"),
                transcript_snapshot=values.get("transcript_snapshot") or [],
                context_snapshot=values.get("context_snapshot") or {},
                closed_at=values.get("closed_at"),
                deleted=False,
                created_at=now,
                updated_at=now,
            )
            .returning(self._ticket)
        )
        row = dict(result.mappings().one())
        self._session.commit()
        return row

    def list_page(self, page: int = 1, page_size: int = 20, status: str | None = None) -> tuple[list[dict[str, Any]], int]:
        conditions = [self._ticket.c.deleted.is_(False)]
        if status:
            conditions.append(self._ticket.c.status == status)
        total = self._session.execute(
            sa.select(sa.func.count()).select_from(self._ticket).where(*conditions)
        ).scalar_one()
        rows = self._session.execute(
            sa.select(self._ticket)
            .where(*conditions)
            .order_by(self._ticket.c.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).mappings().all()
        return [dict(row) for row in rows], int(total)

    def get(self, ticket_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._ticket).where(self._ticket.c.id == ticket_id, self._ticket.c.deleted.is_(False))
        ).mappings().one_or_none()
        return dict(row) if row else None

    def update(self, ticket_id: int, values: dict[str, Any]) -> dict[str, Any] | None:
        row = self._session.execute(
            self._ticket.update()
            .where(self._ticket.c.id == ticket_id, self._ticket.c.deleted.is_(False))
            .values(**values, updated_at=datetime.now())
            .returning(self._ticket)
        ).mappings().one_or_none()
        self._session.commit()
        return dict(row) if row else None
