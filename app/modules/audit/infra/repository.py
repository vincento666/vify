from __future__ import annotations

from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.host.context import RequestContext
from app.core.sanitization import sanitize_value
from app.core.schema import register_baseline_tables

register_baseline_tables()


class AuditRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._audit = Base.metadata.tables["audit_record"]

    def record(
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: str | int,
        status: str = "succeeded",
        metadata: dict[str, Any] | None = None,
        actor: str | None = None,
        request_context: RequestContext | None = None,
    ) -> dict[str, Any]:
        now = datetime.now()
        row_metadata = dict(metadata or {})
        if request_context is not None:
            row_metadata["requestContext"] = request_context.audit_metadata()
        row_actor = actor or (request_context.actor_id if request_context is not None else "system")
        row = self._session.execute(
            self._audit.insert()
            .values(
                actor=row_actor,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id),
                status=status,
                metadata=sanitize_value(row_metadata),
                deleted=False,
                created_at=now,
                updated_at=now,
            )
            .returning(self._audit)
        ).mappings().one()
        self._session.commit()
        return dict(row)

    def list_page(
        self,
        page: int = 1,
        page_size: int = 20,
        action: str | None = None,
        resource_type: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions = [self._audit.c.deleted.is_(False)]
        if action:
            conditions.append(self._audit.c.action == action)
        if resource_type:
            conditions.append(self._audit.c.resource_type == resource_type)
        total = self._session.execute(
            sa.select(sa.func.count()).select_from(self._audit).where(*conditions)
        ).scalar_one()
        rows = self._session.execute(
            sa.select(self._audit)
            .where(*conditions)
            .order_by(self._audit.c.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).mappings().all()
        return [dict(row) for row in rows], int(total)

    def count_failed_channel_deliveries(self) -> int:
        return int(
            self._session.execute(
                sa.select(sa.func.count())
                .select_from(self._audit)
                .where(
                    self._audit.c.deleted.is_(False),
                    self._audit.c.action == "CHANNEL_DELIVERY_FAILED",
                    self._audit.c.status == "failed",
                )
            ).scalar_one()
        )
