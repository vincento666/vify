from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.database import Base
from app.core.db_write import insert_and_fetch
from app.core.schema import register_baseline_tables

register_baseline_tables()


class McpServerRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._mcp_server = Base.metadata.tables["mcp_server"]

    def list_page(
        self,
        page: int,
        page_size: int,
        enabled: bool | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[ColumnElement[bool]] = [self._mcp_server.c.deleted.is_(False)]
        if enabled is not None:
            conditions.append(self._mcp_server.c.enabled.is_(enabled))
        total = self._session.execute(
            sa.select(sa.func.count()).select_from(self._mcp_server).where(*conditions)
        ).scalar_one()
        rows = self._session.execute(
            sa.select(self._mcp_server)
            .where(*conditions)
            .order_by(self._mcp_server.c.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).mappings().all()
        return [dict(row) for row in rows], int(total)

    def create(self, values: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now()
        row = insert_and_fetch(
            self._session,
            self._mcp_server,
            {
                **values,
                "enabled": True,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        self._session.commit()
        return row

    def get(self, server_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._mcp_server).where(
                self._mcp_server.c.id == server_id,
                self._mcp_server.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def update(self, server_id: int, values: dict[str, Any]) -> dict[str, Any] | None:
        if not values:
            return self.get(server_id)
        values["updated_at"] = datetime.now()
        self._session.execute(
            self._mcp_server.update()
            .where(self._mcp_server.c.id == server_id, self._mcp_server.c.deleted.is_(False))
            .values(**values)
        )
        self._session.commit()
        return self.get(server_id)

    def delete(self, server_id: int) -> bool:
        result = self._session.execute(
            self._mcp_server.update()
            .where(self._mcp_server.c.id == server_id, self._mcp_server.c.deleted.is_(False))
            .values(deleted=True, updated_at=datetime.now())
        )
        self._session.commit()
        return isinstance(result, CursorResult) and result.rowcount > 0
